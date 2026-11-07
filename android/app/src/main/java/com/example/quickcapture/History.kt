package com.example.quickcapture

import android.content.Context
import org.json.JSONObject
import java.io.File

/** Small local log of recent captures (shown on the main screen). */
class History(ctx: Context) {
    private val file = File(ctx.filesDir, "history.jsonl")

    class Entry(val ts: String, val title: String, val file: String, val saved: Boolean)

    @Synchronized fun add(ts: String, title: String, fileName: String, saved: Boolean) {
        file.appendText(JSONObject().put("ts", ts).put("title", title).put("file", fileName).put("saved", saved).toString() + "\n")
        val lines = file.readLines()
        if (lines.size > 300) file.writeText(lines.takeLast(200).joinToString("\n") + "\n")
    }

    @Synchronized fun markSaved(names: Collection<String>) {
        if (names.isEmpty() || !file.exists()) return
        file.writeText(file.readLines().filter { it.isNotBlank() }.joinToString("\n") { line ->
            val o = JSONObject(line)
            if (o.getString("file") in names) o.put("saved", true)
            o.toString()
        } + "\n")
    }

    @Synchronized fun recent(n: Int = 25): List<Entry> {
        if (!file.exists()) return emptyList()
        return file.readLines().filter { it.isNotBlank() }.takeLast(n).reversed().mapNotNull {
            runCatching {
                val o = JSONObject(it); Entry(o.getString("ts"), o.getString("title"), o.getString("file"), o.optBoolean("saved", true))
            }.getOrNull()
        }
    }
}
