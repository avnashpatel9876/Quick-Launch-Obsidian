package com.example.quickcapture

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.view.ViewGroup.LayoutParams.MATCH_PARENT
import android.view.ViewGroup.LayoutParams.WRAP_CONTENT
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import java.util.concurrent.Executors

/** Setup screen: pick the vault folder (SAF), see status, retry queued notes, browse recent captures. */
class MainActivity : Activity() {
    private lateinit var statusView: TextView
    private lateinit var folderInput: EditText
    private lateinit var recentView: TextView
    private val io = Executors.newSingleThreadExecutor()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(20), dp(20), dp(20))
            fitsSystemWindows = true
        }
        box.addView(TextView(this).apply { text = "Quick Capture"; textSize = 24f })
        statusView = TextView(this).apply { textSize = 15f; setPadding(0, dp(12), 0, dp(12)) }
        box.addView(statusView)

        box.addView(Button(this).apply { text = "Choose vault folder"; setOnClickListener { pickFolder() } })
        box.addView(TextView(this).apply {
            text = "Pick the vault's root folder (the one that contains .obsidian). Notes go into the sub-folder below."
            textSize = 13f
        })
        folderInput = EditText(this).apply { hint = "Capture sub-folder (blank = picked folder itself)"; setSingleLine(true) }
        box.addView(folderInput, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT))
        box.addView(Button(this).apply { text = "Save sub-folder name"; setOnClickListener { saveFolderName() } })

        box.addView(Button(this).apply { text = "New capture"; setOnClickListener {
            startActivity(Intent(this@MainActivity, CaptureActivity::class.java)) } })
        box.addView(Button(this).apply { text = "Retry queued notes"; setOnClickListener { retryPending() } })

        box.addView(TextView(this).apply { text = "Recent captures"; textSize = 18f; setPadding(0, dp(16), 0, dp(4)) })
        recentView = TextView(this).apply { textSize = 14f }
        box.addView(recentView)

        setContentView(ScrollView(this).apply { addView(box) })
        folderInput.setText(VaultStore(this).captureFolder)
    }

    override fun onResume() {
        super.onResume()
        refresh()
        retryPending(quiet = true)
    }

    private fun pickFolder() {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE).addFlags(
            Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION or
                    Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION or Intent.FLAG_GRANT_PREFIX_URI_PERMISSION)
        @Suppress("DEPRECATION") startActivityForResult(intent, REQ_TREE)
    }

    @Suppress("DEPRECATION")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQ_TREE || resultCode != RESULT_OK) return
        val uri = data?.data ?: return
        val app = applicationContext
        val folderName = folderInput.text.toString()
        io.execute {
            val msg = try {
                val store = VaultStore(app)
                store.setPickedFolder(uri)
                store.captureFolder = folderName
                store.verify()                                  // creates the capture folder, proves we can write
                History(app).markSaved(store.flushPending())
                "Vault folder ready"
            } catch (e: Exception) {
                "Could not use that folder: ${e.message}"
            }
            runOnUiThread { Toast.makeText(this, msg, Toast.LENGTH_LONG).show(); refresh() }
        }
    }

    private fun saveFolderName() {
        VaultStore(this).captureFolder = folderInput.text.toString()
        folderInput.setText(VaultStore(this).captureFolder)
        Toast.makeText(this, "Saved", Toast.LENGTH_SHORT).show()
    }

    private fun retryPending(quiet: Boolean = false) {
        val app = applicationContext
        io.execute {
            val store = VaultStore(app)
            val before = store.pendingCount()
            val done = store.flushPending()
            History(app).markSaved(done)
            runOnUiThread {
                refresh()
                if (!quiet) Toast.makeText(this, if (before == 0) "Nothing queued" else "${done.size} of $before synced",
                    Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun refresh() {
        val store = VaultStore(this)
        val queued = store.pendingCount()
        statusView.text = buildString {
            append(when {
                store.treeUri == null -> "Vault folder: not set yet"
                !store.hasAccess() -> "Vault folder: access was lost - choose it again"
                else -> "Vault folder: ${store.pickedFolderName() ?: "selected"}  \u2713"
            })
            if (queued > 0) append("\nQueued on phone: $queued")
        }
        val rows = History(this).recent()
        recentView.text = if (rows.isEmpty()) "Nothing yet" else rows.joinToString("\n") {
            "${if (it.saved) "\u2713" else "\u23F3"}  ${it.ts.take(16).replace('T', ' ')}  ${it.title}"
        }
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    companion object { private const val REQ_TREE = 1 }
}
