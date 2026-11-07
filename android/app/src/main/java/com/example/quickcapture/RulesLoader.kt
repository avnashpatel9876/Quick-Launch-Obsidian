package com.example.quickcapture

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/** Reads assets/rules.json (shared with the Windows app via ../shared). */
object RulesLoader {
    @Volatile private var cached: Rules? = null

    fun load(ctx: Context): Rules = cached ?: synchronized(this) {
        cached ?: parse(ctx.assets.open("rules.json").bufferedReader().use { it.readText() }).also { cached = it }
    }

    private fun pairs(arr: JSONArray, nameKey: String): List<Pair<String, List<String>>> =
        (0 until arr.length()).map { i ->
            val o = arr.getJSONObject(i)
            val kw = o.getJSONArray("keywords")
            o.getString(nameKey) to (0 until kw.length()).map { kw.getString(it) }
        }

    fun parse(json: String): Rules {
        val o = JSONObject(json)
        return Rules.of(
            o.optString("default_category", "Unsorted"),
            pairs(o.getJSONArray("categories"), "name"),
            pairs(o.getJSONArray("tags"), "tag"),
        )
    }
}
