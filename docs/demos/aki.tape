# Records the AKI preflight demo to MP4 + GIF.
#   needs: the Inspector backend up on :8200 (PREFLIGHT_DB_URL -> test bed)
#   run:   vhs aki.tape   (from docs/demos)
Output aki-preflight.mp4
Output aki-preflight.gif

Require python3

Set Shell "zsh"
Set FontSize 19
Set Width 1280
Set Height 760
Set Padding 26
Set Theme "Catppuccin Mocha"
Set TypingSpeed 35ms

Hide
Type "cd /Volumes/extraSupply/Projects/psdl-inspector/docs/demos && clear"
Enter
Show

Sleep 700ms
Type "DEMO_PACE=1.7 python3 demo.py --auto"
Sleep 800ms
Enter
Sleep 13s
