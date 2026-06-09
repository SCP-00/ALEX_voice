#!/bin/bash
# setup_chrome_for_browser_use.sh
# Configura Chromium del sistema para que browser-use pueda lanzarlo.
# Ejecutar como root.

set -e

CHROMIUM_ELF="/usr/lib/chromium/chromium"
WRAPPER_PATH="/usr/bin/google-chrome"

if [ ! -f "$CHROMIUM_ELF" ]; then
    echo "❌ Chromium ELF not found at $CHROMIUM_ELF"
    echo "   Install chromium first: apt install chromium -y"
    exit 1
fi

echo "=== Step 1: Compile C wrapper (adds --no-sandbox) ==="
cat > /tmp/chrome_wrapper.c << 'EOF'
#include <unistd.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    char **new_argv = malloc((argc + 3) * sizeof(char*));
    new_argv[0] = "/usr/lib/chromium/chromium";
    new_argv[1] = "--no-sandbox";
    new_argv[2] = "--disable-setuid-sandbox";
    for (int i = 1; i < argc; i++) {
        new_argv[i + 2] = argv[i];
    }
    new_argv[argc + 2] = NULL;
    execv(new_argv[0], new_argv);
    free(new_argv);
    return 1;
}
EOF
gcc -O2 -o /tmp/chrome_wrapper /tmp/chrome_wrapper.c
echo "✅ Compiled C wrapper"

echo "=== Step 2: Install wrapper at standard paths ==="
rm -f /usr/bin/google-chrome /usr/bin/google-chrome-stable /usr/bin/chromium-browser
cp /tmp/chrome_wrapper "$WRAPPER_PATH"
chmod +x "$WRAPPER_PATH"
ln -sf "$WRAPPER_PATH" /usr/bin/google-chrome-stable
ln -sf "$WRAPPER_PATH" /usr/bin/chromium-browser
echo "✅ Wrapper installed at /usr/bin/google-chrome (chromium + --no-sandbox)"

echo "=== Step 3: Create /opt/google/chrome/chrome (Puppeteer path) ==="
mkdir -p /opt/google/chrome
cp "$WRAPPER_PATH" /opt/google/chrome/chrome
chmod +x /opt/google/chrome/chrome
echo "✅ Chrome also at /opt/google/chrome/chrome"

echo "=== Step 4: Set environment variables ==="
echo 'export CHROME_BIN=/usr/bin/google-chrome' > /etc/profile.d/chrome.sh
echo 'export PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright' >> /etc/profile.d/chrome.sh
chmod +x /etc/profile.d/chrome.sh

# Also add to /etc/environment for services
grep -q 'CHROME_BIN' /etc/environment || echo 'CHROME_BIN=/usr/bin/google-chrome' >> /etc/environment
grep -q 'PLAYWRIGHT_BROWSERS_PATH' /etc/environment || echo 'PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright' >> /etc/environment

export CHROME_BIN=/usr/bin/google-chrome
export PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
echo "✅ Environment configured"

echo "=== Step 5: Verify ==="
"$WRAPPER_PATH" --version
file "$WRAPPER_PATH"
echo ""
echo "🎉 Setup complete! Browser-use should now find Chrome at:"
echo "   - /usr/bin/google-chrome"
echo "   - /usr/bin/google-chrome-stable"
echo "   - /usr/bin/chromium-browser"
echo "   - /opt/google/chrome/chrome"
echo ""
echo "Test: run 'browser-use' with url=http://localhost:8081/health"
