import os
import sys
import subprocess
import shutil

def run_cmd(cmd, cwd=None):
    print(f"\n[RUNNING] {cmd}")
    res = subprocess.run(cmd, shell=True, cwd=cwd)
    if res.returncode != 0:
        print(f"[ERROR] Command failed with exit code {res.returncode}: {cmd}")
        return False
    return True

def main():
    print("=" * 60)
    print("  LAUNCHING OCULAR TOXICITY AI WEB APPLICATION")
    print("=" * 60)
    
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(workspace_dir, "frontend")
    dist_dir = os.path.join(frontend_dir, "dist")
    
    # 1. Build Frontend if npm is installed
    npm_path = shutil.which("npm")
    if npm_path:
        print("\n[1/2] Checking React frontend build...")
        node_modules = os.path.join(frontend_dir, "node_modules")
        if not os.path.exists(node_modules):
            print("Installing frontend npm dependencies...")
            run_cmd("npm install", cwd=frontend_dir)
            
        print("Compiling React production build...")
        run_cmd("npm run build", cwd=frontend_dir)
    else:
        print("\n[NOTICE] 'npm' was not detected on system PATH. Starting FastAPI backend directly...")
        print("If developing frontend, run 'npm install && npm run dev' inside the frontend/ directory.")

    # 2. Launch FastAPI backend
    print("\n[2/2] Starting FastAPI backend server at http://127.0.0.1:8000...")
    print("Press Ctrl+C to stop the server.\n")
    
    import uvicorn
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    main()
