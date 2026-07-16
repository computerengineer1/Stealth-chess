import os
import sys
import subprocess
import shutil

def run_command(command, description):
    print(f"\n[+] Running: {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, text=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"[-] Error during: {description}. Details: {e}")
        return False

def main():
    # Ensure working directory is the project root (where main.py is located)
    if not os.path.exists("main.py") and os.path.exists("../main.py"):
        os.chdir("..")
        print(f"[+] Changed working directory to project root: {os.getcwd()}")

    print("="*60)
    print("         Chess Bot Nuitka Compiler Script")
    print("="*60)

    # 1. Install/Update pip requirements
    if os.path.exists("requirements.txt"):
        run_command("pip install -r requirements.txt", "Installing project dependencies")
    else:
        print("[-] requirements.txt not found. Skipping dependency installation.")

    # 2. Ensure Nuitka and icon utilities are installed
    run_command("pip install nuitka Pillow imageio", "Installing Nuitka compiler and icon processing dependencies")

    # 3. Convert logo.png to logo.ico using Pillow
    if os.path.exists("logo.png"):
        print("\n[+] Converting logo.png to logo.ico...")
        try:
            from PIL import Image
            img = Image.open("logo.png")
            img.save("logo.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
            print("[+] Successfully created logo.ico.")
        except Exception as e:
            print(f"[-] Failed to convert logo.png to logo.ico: {e}")

    # 4. Create the Nuitka build command
    # We use --standalone to create a distribution folder.
    # We use --enable-plugin=pyqt6 so Nuitka packages PyQt6 dependencies properly.
    # We include stockfish and templates in the distribution.
    # We disable console mode (--windows-console-mode=disable) so no cmd window pops up.
    
    nuitka_cmd = (
        "python -m nuitka "
        "--standalone "
        "--enable-plugin=pyqt6 "
        "--windows-console-mode=disable "
    )
    
    if os.path.exists("logo.ico"):
        nuitka_cmd += "--windows-icon-from-ico=logo.ico "
        
    nuitka_cmd += "--include-data-file=stockfish-windows-x86-64-avx2.exe=stockfish-windows-x86-64-avx2.exe "
    
    if os.path.exists("logo.png"):
        nuitka_cmd += "--include-data-file=logo.png=logo.png "
        
    nuitka_cmd += "--output-dir=build_output main.py"


    print(f"\n[+] Compilation Command:\n{nuitka_cmd}\n")
    
    print("[+] Starting compilation automatically (Non-Interactive mode)...")
    success = run_command(nuitka_cmd, "Compiling Chess Bot to native executable")

    if success:
        print("\n" + "="*60)
        print("[*] SUCCESS: Chess Bot compiled successfully!")
        print("Output directory: ./build_output/main.dist/")
        print("="*60)
        
        # Copy the extension folder to build_output for ease of packaging
        if os.path.exists("extension"):
            target_ext = os.path.join("build_output", "extension")
            if os.path.exists(target_ext):
                shutil.rmtree(target_ext)
            shutil.copytree("extension", target_ext)
            print("[+] Copied 'extension' folder to build_output.")
            
        print("\nHow to distribute to your subscribers:")
        print("1. Zip the contents of 'build_output/main.dist' along with the 'extension' folder.")
        print("2. Send the zip file to your subscribers.")
        print("3. Subscribers will load the Chrome Extension in developer mode, launch 'main.exe', and enter their key.")
    else:
        print("\n[-] Compilation failed. Please read the error log above.")

if __name__ == "__main__":
    main()
