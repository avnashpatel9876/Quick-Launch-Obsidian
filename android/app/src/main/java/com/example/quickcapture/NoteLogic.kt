package com.example.quickcapture

import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter

/**
 * Pure note logic - a line-for-line port of windows/qc_core.py.
 * No Android imports on purpose, so it can be tested on a plain JVM against
 * shared/test_vectors.json. Keep the two files in sync.
 */
class Rules(
    val defaultCategory: String,
    val categories: List<Pair<String, Regex>>,
    val tags: List<Pair<String, Regex>>,
) {
    companion object {
        fun of(
            defaultCategory: String,
            categories: List<Pair<String, List<String>>>,
            tags: List<Pair<String, List<String>>>,
        ) = Rules(
            defaultCategory,
            categories.map { it.first to keywordRegex(it.second) },
            tags.map { it.first to keywordRegex(it.second) },
        )

        // Keyword must start at a word boundary: "work" matches "workflow", not "network".
        private fun keywordRegex(words: List<String>) = Regex(
            "(?<![\\p{L}\\p{N}_])(?:" + words.joinToString("|") { Regex.escape(it.lowercase()) } + ")"
        )
    }
}

class Note(val fileName: String, val markdown: String, val title: String, val category: String)

object NoteLogic {
    private val TITLE_PREFIX = Regex("^(?:#{1,6}\\s+|>\\s*|[-*]\\s+(?:\\[[ xX]\\]\\s+)?)")
    private val SLUG_BAD = Regex("[^\\p{L}\\p{N}_-]+")
    private val DASHES = Regex("-{2,}")
    private val FOLDER_SPLIT = Regex("[\\\\/]+")
    private val FOLDER_BAD = Regex("[<>:\"|?*\\u0000-\\u001f]")
    private val STAMP = DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss")
    private val HUMAN = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm")
    private val ISO = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssxxx")

    fun categorize(text: String, rules: Rules): String {
        val t = text.lowercase()
        for ((name, rx) in rules.categories) if (rx.containsMatchIn(t)) return name
        return rules.defaultCategory
    }

    fun tagsFor(text: String, category: String, rules: Rules): List<String> {
        val t = text.lowercase()
        val out = sortedSetOf(category.lowercase())
        for ((tag, rx) in rules.tags) if (rx.containsMatchIn(t)) out.add(tag)
        return out.toList()
    }

    /** With no explicit title, a short first body line becomes the title and leaves the body. */
    fun splitTitle(title: String, body: String): Pair<String, String> {
        val t = title.trim()
        val b = body.trim()
        if (t.isNotEmpty()) return t to b
        val lines = b.lines()
        for ((i, line) in lines.withIndex()) {
            val s = line.trim()
            if (s.isEmpty()) continue
            if (s.startsWith("![[")) break
            val cleaned = TITLE_PREFIX.replaceFirst(s, "").trim()
            if (cleaned.isNotEmpty() && cleaned.length <= 80) {
                return cleaned to lines.drop(i + 1).joinToString("\n").trim()
            }
            break
        }
        return "" to b
    }

    fun slugify(s: String): String {
        var x = SLUG_BAD.replace(s.lowercase(), "-")
        x = DASHES.replace(x, "-").trim('-')
        if (x.length > 40) x = x.substring(0, 40).trim('-')
        return x.ifEmpty { "capture" }
    }

    /** Safe vault-relative folder path ("" allowed, no "..", "/"-separated). */
    fun sanitizeFolder(name: String): String =
        name.split(FOLDER_SPLIT).map { it.trim() }
            .filter { it != "" && it != "." && it != ".." }
            .joinToString("/") { FOLDER_BAD.replace(it, "-") }

    fun buildNote(title: String, body: String, source: String,
                  now: OffsetDateTime, uniq: String, rules: Rules): Note {
        val (t, rest) = splitTitle(title, body)
        val text = (t + "\n" + rest).trim()
        val category = categorize(text, rules)
        val tags = tagsFor(text, category, rules)
        val heading = t.ifEmpty { "Capture " + now.format(HUMAN) }
        val short = source.substringBefore('-').take(3)
        val fileName = "${now.format(STAMP)}-$short-$uniq-${slugify(t)}.md"
        val md = StringBuilder()
            .append("---\n")
            .append("created: ").append(now.format(ISO)).append('\n')
            .append("source: ").append(source).append('\n')
            .append("category: ").append(category).append('\n')
            .append("tags: [").append(tags.joinToString(", ")).append("]\n")
            .append("---\n\n")
            .append("# ").append(heading).append('\n')
        if (rest.isNotEmpty()) md.append('\n').append(rest).append('\n')
        return Note(fileName, md.toString(), heading, category)
    }
}
