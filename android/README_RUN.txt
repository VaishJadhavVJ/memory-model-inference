Memory-model tests for Android phones (no root needed)

1. Install Termux from F-Droid: https://f-droid.org/packages/com.termux/
   (not the Play Store version, which is out of date).

2. Open Termux and type:
     pkg install clang make unzip
   Answer Y to any question.

3. Copy android_tests.zip to the phone's Downloads folder. Then type in Termux:
     termux-setup-storage
   Tap Allow, then type:
     unzip ~/storage/downloads/android_tests.zip -d ~
     cd ~/android_tests

4. Type:
     termux-wake-lock
   Keep the phone plugged in, with the screen on and Termux open, until step 5 finishes.

5. Type:
     sh build_and_run.sh
   It builds the tests, then runs them one by one and shows its progress.

6. When it prints "Done", send back the file results_<phone>_<date>.txt.
   A copy is in your Downloads folder.
