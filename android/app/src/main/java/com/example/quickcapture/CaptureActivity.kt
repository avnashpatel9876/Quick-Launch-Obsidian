package com.example.quickcapture

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.speech.RecognizerIntent
import android.view.Gravity
import android.view.ViewGroup.LayoutParams.MATCH_PARENT
import android.view.ViewGroup.LayoutParams.WRAP_CONTENT
import android.view.WindowManager
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import java.time.OffsetDateTime
import java.util.UUID
import java.util.concurrent.Executors

/** The floating capture panel: opened by the widget or Android's Share sheet. Obsidian is never launched. */
class CaptureActivity : Activity() {
    private lateinit var titleField: EditText
    private lateinit var bodyField: EditText
    private lateinit var saveBtn: Button
    private var isShare = false
    private var skipDraftSave = false
    private val prefs by lazy { getSharedPreferences("qc", MODE_PRIVATE) }
    private val io = Executors.newSingleThreadExecutor()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setFinishOnTouchOutside(false)                       // a stray tap must not lose a thought
        window.setLayout((resources.displayMetrics.widthPixels * 0.94).toInt(), WRAP_CONTENT)
        window.setGravity(Gravity.TOP)
        window.attributes = window.attributes.apply { y = dp(56) }
        window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_VISIBLE or
                WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE)
        buildUi()
        populate(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        saveDraft()
        setIntent(intent)
        skipDraftSave = false
        populate(intent)
    }

    override fun onPause() { super.onPause(); saveDraft() }

    private fun buildUi() {
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(14), dp(16), dp(10))
        }
        box.addView(TextView(this).apply { text = "Quick Capture"; textSize = 20f })
        titleField = EditText(this).apply { hint = "Title (optional)"; setSingleLine(true) }
        box.addView(titleField, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT))
        bodyField = EditText(this).apply {
            hint = "Write your idea…"; minLines = 5; gravity = Gravity.TOP or Gravity.START
        }
        box.addView(bodyField, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT))
        val row = LinearLayout(this).apply { gravity = Gravity.END }
        row.addView(Button(this).apply { text = "Voice"; setOnClickListener { startVoice() } })
        saveBtn = Button(this).apply { text = "Save"; setOnClickListener { save() } }
        row.addView(saveBtn)
        box.addView(row)
        setContentView(box)
    }

    private fun populate(i: Intent?) {
        isShare = i?.action == Intent.ACTION_SEND
        if (isShare) {
            titleField.setText(i?.getCharSequenceExtra(Intent.EXTRA_SUBJECT)?.toString().orEmpty())
            bodyField.setText(i?.getCharSequenceExtra(Intent.EXTRA_TEXT)?.toString().orEmpty())
        } else {                                              // restore the autosaved draft
            titleField.setText(prefs.getString("draft_title", "").orEmpty())
            bodyField.setText(prefs.getString("draft_body", "").orEmpty())
        }
        bodyField.setSelection(bodyField.text.length)
        bodyField.requestFocus()
    }

    // ---- drafts (not used for shared text, so an unfinished typed draft survives a share) ----
    private fun saveDraft() {
        if (isShare || skipDraftSave || !::titleField.isInitialized) return
        prefs.edit().putString("draft_title", titleField.text.toString())
            .putString("draft_body", bodyField.text.toString()).apply()
    }

    private fun clearDraft() {
        if (!isShare) prefs.edit().remove("draft_title").remove("draft_body").apply()
    }

    // ---- voice ----
    private fun startVoice() {
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            .putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
        try {
            @Suppress("DEPRECATION") startActivityForResult(intent, REQ_VOICE)
        } catch (e: Exception) {
            Toast.makeText(this, "Speech recognition is not available on this device", Toast.LENGTH_SHORT).show()
        }
    }

    @Suppress("DEPRECATION")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQ_VOICE || resultCode != RESULT_OK) return
        val text = data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull() ?: return
        val cur = bodyField.text
        if (cur.isNotEmpty() && !cur.last().isWhitespace()) cur.append(' ')
        cur.append(text)
        bodyField.setSelection(cur.length)
    }

    // ---- save ----
    private fun save() {
        val title = titleField.text.toString()
        val body = bodyField.text.toString()
        if (title.isBlank() && body.isBlank()) return
        saveBtn.isEnabled = false
        val source = if (isShare) "android-share" else "android-widget"
        val app = applicationContext
        io.execute {
            try {
                val now = OffsetDateTime.now()
                val note = NoteLogic.buildNote(title, body, source, now,
                    UUID.randomUUID().toString().take(6), RulesLoader.load(app))
                val store = VaultStore(app)
                val result = store.save(note)
                val hist = History(app)
                hist.add(now.toString(), note.title, note.fileName, result is VaultStore.Result.Saved)
                if (result is VaultStore.Result.Saved) hist.markSaved(store.flushPending())
                runOnUiThread {
                    skipDraftSave = true
                    clearDraft()
                    val msg = when (result) {
                        is VaultStore.Result.Saved -> "Saved"
                        is VaultStore.Result.Queued -> "Saved on phone, will sync to vault when possible (${result.reason})"
                    }
                    Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
                    finish()
                }
            } catch (e: Exception) {
                runOnUiThread {
                    saveBtn.isEnabled = true
                    Toast.makeText(this, "Could not save: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    companion object { private const val REQ_VOICE = 9 }
}
