const fs = require('fs');
const path = require('path');

const srcDir = path.join(__dirname, 'ios_stealth_patch');
const targets = [
    path.join(__dirname, 'node_modules', 'cordova-plugin-inappbrowser', 'src', 'ios'),
    path.join(__dirname, 'ios', 'capacitor-cordova-ios-plugins', 'sources', 'CordovaPluginInappbrowser')
];

const files = ['CDVWKInAppBrowser.m', 'CDVWKInAppBrowser.h'];

console.log("Stealth Assist iOS Patching started...");

files.forEach(file => {
    const srcFile = path.join(srcDir, file);
    if (!fs.existsSync(srcFile)) {
        console.error(`[-] Source file not found: ${srcFile}`);
        return;
    }
    
    targets.forEach(targetDir => {
        if (!fs.existsSync(targetDir)) {
            console.log(`[i] Target directory does not exist (skipping): ${targetDir}`);
            return;
        }
        
        const destFile = path.join(targetDir, file);
        try {
            fs.copyFileSync(srcFile, destFile);
            console.log(`[+] Successfully patched: ${destFile}`);
        } catch (err) {
            console.error(`[-] Failed to copy to ${destFile}:`, err.message);
        }
    });
});

console.log("Stealth Assist iOS Patching completed.");
