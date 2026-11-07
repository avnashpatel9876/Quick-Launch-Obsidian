package com.example.quickcapture

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.DocumentsContract
import android.provider.DocumentsContract.Document
import java.io.File
import java.io.IOException

/**
 * Writes notes into the Obsidian vault through the Storage Access Framework.
 * The user picks the vault folder once; the persisted tree URI keeps write access
 * across reboots. If a write fails, the note is parked in app-private storage and
 * retried later, so a capture is never lost.
 */
class VaultStore(private val ctx: Context) {
    private val prefs = ctx.getSharedPreferences("qc", Context.MODE_PRIVATE)
    private val cr = ctx.contentResolver
    private val pendingDir = File(ctx.filesDir, "pending").apply { mkdirs() }

    sealed class Result {
        object Saved : Result()
        class Queued(val reason: String) : Result()
    }

    // ---- settings ----------------------------------------------------------
    var treeUri: Uri?
        get() = prefs.getString("tree_uri", null)?.let(Uri::parse)
        private set(v) { prefs.edit().putString("tree_uri", v?.toString()).apply() }

    /** Sub-folder inside the picked folder. Blank = write directly into the picked folder. */
    var captureFolder: String
        get() = prefs.getString("folder", "Quick Capture").orEmpty()
        set(v) { prefs.edit().putString("folder", NoteLogic.sanitizeFolder(v)).apply() }

    fun setPickedFolder(uri: Uri) {
        val rw = Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
        val old = treeUri
        cr.takePersistableUriPermission(uri, rw)
        if (old != null && old != uri) runCatching { cr.releasePersistableUriPermission(old, rw) }
        treeUri = uri
    }

    fun hasAccess(): Boolean {
        val u = treeUri ?: return false
        return cr.persistedUriPermissions.any { it.uri == u && it.isWritePermission }
    }

    fun pickedFolderName(): String? = treeUri?.let { tree ->
        runCatching {
            val doc = DocumentsContract.buildDocumentUriUsingTree(tree, DocumentsContract.getTreeDocumentId(tree))
            cr.query(doc, arrayOf(Document.COLUMN_DISPLAY_NAME), null, null, null)?.use {
                if (it.moveToFirst()) it.getString(0) else null
            }
        }.getOrNull()
    }

    // ---- saving ------------------------------------------------------------
    /** Never throws: falls back to the pending queue. */
    fun save(note: Note): Result {
        if (!hasAccess()) { queue(note); return Result.Queued("No vault folder access yet") }
        return try {
            write(note.fileName, note.markdown)
            Result.Saved
        } catch (e: Exception) {
            queue(note); Result.Queued(e.message ?: e.javaClass.simpleName)
        }
    }

    /** Creates the capture folder if needed; use to surface problems at pick time. */
    fun verify() { captureDirId() }

    fun pendingCount(): Int = pendingDir.listFiles()?.size ?: 0

    /** Retries queued notes. Returns the file names that made it into the vault. */
    fun flushPending(): List<String> {
        if (!hasAccess()) return emptyList()
        val done = mutableListOf<String>()
        for (f in pendingDir.listFiles().orEmpty().sortedBy { it.name }) {
            try {
                write(f.name, f.readText(Charsets.UTF_8))
                f.delete(); done += f.name
            } catch (_: Exception) { break }          // vault still unreachable; keep the rest
        }
        return done
    }

    private fun queue(note: Note) = File(pendingDir, note.fileName).writeText(note.markdown, Charsets.UTF_8)

    private fun write(name: String, text: String) {
        val tree = treeUri ?: throw IOException("No vault folder selected")
        val dirUri = DocumentsContract.buildDocumentUriUsingTree(tree, captureDirId())
        val file = DocumentsContract.createDocument(cr, dirUri, "text/markdown", name)
            ?: throw IOException("Could not create $name")
        try {
            (cr.openOutputStream(file, "wt") ?: throw IOException("Could not open $name"))
                .use { it.write(text.toByteArray(Charsets.UTF_8)) }
        } catch (e: Exception) {
            runCatching { DocumentsContract.deleteDocument(cr, file) }   // don't leave an empty note behind
            throw e
        }
    }

    // ---- SAF helpers -------------------------------------------------------
    private fun captureDirId(): String {
        val tree = treeUri ?: throw IOException("No vault folder selected")
        var id = DocumentsContract.getTreeDocumentId(tree)
        for (part in NoteLogic.sanitizeFolder(captureFolder).split('/').filter { it.isNotEmpty() }) {
            id = findDir(tree, id, part) ?: createDir(tree, id, part)
        }
        return id
    }

    private fun findDir(tree: Uri, parentId: String, name: String): String? {
        val children = DocumentsContract.buildChildDocumentsUriUsingTree(tree, parentId)
        cr.query(children, arrayOf(Document.COLUMN_DOCUMENT_ID, Document.COLUMN_DISPLAY_NAME, Document.COLUMN_MIME_TYPE),
            null, null, null)?.use { c ->
            while (c.moveToNext()) {
                if (c.getString(1) == name && c.getString(2) == Document.MIME_TYPE_DIR) return c.getString(0)
            }
        }
        return null
    }

    private fun createDir(tree: Uri, parentId: String, name: String): String {
        val parent = DocumentsContract.buildDocumentUriUsingTree(tree, parentId)
        val created = DocumentsContract.createDocument(cr, parent, Document.MIME_TYPE_DIR, name)
            ?: throw IOException("Could not create folder $name")
        return DocumentsContract.getDocumentId(created)
    }
}
