#!/bin/sh
# Optional sanity check without Android Studio. Needs kotlinc 2.x and an android.jar (API 34).
# 1) compile every Kotlin file against android.jar, 2) run NoteLogic against shared/test_vectors.json.
# usage: android/tools/check_kotlin.sh /path/to/kotlinc/bin/kotlinc /path/to/android.jar
set -e
KOTLINC=$1; ANDROID_JAR=$2
HERE=$(cd "$(dirname "$0")" && pwd); SRC=$HERE/../app/src/main/java/com/example/quickcapture; TMP=$(mktemp -d)
cat > "$TMP/R.kt" <<'KT'
package com.example.quickcapture
object R { object layout { const val widget = 1 }; object id { const val widget_root = 2 } }
KT
"$KOTLINC" -cp "$ANDROID_JAR" -d "$TMP/app" "$SRC"/*.kt "$TMP/R.kt" && echo "all Kotlin sources compile"
python3 "$HERE/gen_harness.py" "$HERE/../../shared" "$TMP/Harness.kt"
"$KOTLINC" "$SRC/NoteLogic.kt" "$TMP/Harness.kt" -d "$TMP/h"
java -cp "$TMP/h:$(dirname "$KOTLINC")/../lib/kotlin-stdlib.jar" com.example.quickcapture.HarnessKt
