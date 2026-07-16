import os
import subprocess
import sys

def run_git(cmd):
    try:
        result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"\n[-] Error executing command: {cmd}")
        print(f"Details: {e.stderr}")
        return None

def main():
    print("="*60)
    print("   Chess Bot Mobile - GitHub Automated Deployer")
    print("="*60)
    
    # 1. Check if Git is installed
    git_ver = run_git("git --version")
    if not git_ver:
        print("[-] Git is not installed on your system. Please install Git from: https://git-scm.com/")
        input("\nPress Enter to exit...")
        return
        
    print(f"[+] Found Git: {git_ver}")
    
    # 2. Reset Git and Initialize fresh to prevent cached large files
    if os.path.exists(".git"):
        print("[+] Resetting Git index and cache to force ignore rules...")
        import shutil
        import stat
        def remove_readonly(func, path, _):
            os.chmod(path, stat.S_IWRITE)
            func(path)
        try:
            shutil.rmtree(".git", onerror=remove_readonly)
            print("[+] Successfully reset local Git cache.")
        except Exception as e:
            print("[-] Could not delete .git directory directly. Running git command to clear cache...")
            run_git("git rm -r --cached .")
            
    print("[+] Initializing a fresh local Git repository...")
    run_git("git init")

        
    # 3. Rename branch to main
    run_git("git branch -M main")
    
    # 4. Ask user for GitHub Private Repo URL
    print("\nInstructions:")
    print("1. Go to https://github.com and create a NEW PRIVATE repository.")
    print("2. Copy its HTTPS URL (should end in .git).")
    
    repo_url = input("\nPlease paste your GitHub repository URL here:\n> ").strip()
    if not repo_url:
        print("[-] URL cannot be empty.")
        input("\nPress Enter to exit...")
        return
        
    # 5. Set up Remote Origin
    run_git("git remote remove origin")
    res_remote = run_git(f"git remote add origin {repo_url}")
    if res_remote is None:
        print("[-] Failed to add remote origin. Please check the URL.")
        input("\nPress Enter to exit...")
        return
    print(f"[+] Connected to remote repository: {repo_url}")
    
    # 6. Add and Commit
    print("\n[+] Adding files to stage...")
    run_git("git add .")
    
    print("[+] Creating initial commit...")
    run_git('git commit -m "Configure GitHub Actions iOS build workflow"')
    
    # 7. Push to GitHub
    print("\n[+] Pushing files to GitHub...")
    print("NOTE: If a Git Login window pops up, please log in to authorize.")
    
    # Use standard push
    res_push = run_git("git push -u origin main --force")
    
    if res_push is not None:
        print("\n" + "="*60)
        print("[*] SUCCESS: Your project has been uploaded to GitHub!")
        print("[*] Instructions for IPA build:")
        print("    1. Go to your repository link on github.com.")
        print("    2. Click on the 'Actions' tab at the top.")
        print("    3. Select 'Build iOS IPA (Unsigned)' on the left menu.")
        print("    4. Click 'Run workflow' -> 'Run workflow' (Green button).")
        print("    5. Wait 5 minutes, download the ZIP artifact, and install with ESign!")
        print("="*60)
    else:
        print("\n[-] Push failed. Please ensure you have permission to push to this repo.")
        
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
