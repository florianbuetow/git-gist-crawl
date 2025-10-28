#!/usr/bin/env python3
"""
Git Repository Crawler with GitIngest Integration

Clones/pulls GitHub repositories and generates gists using gitingest.com
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import shutil
import json


class GitIngestGenerator:
    """Generate repository digests using gitingest.com"""

    def __init__(self, download_dir: Optional[Path] = None):
        self.driver = None
        self.download_dir = download_dir or Path.cwd() / ".temp-downloads"
        self.download_dir.mkdir(exist_ok=True)

    def setup_driver(self):
        """Initialize headless Chrome driver for Selenium with download directory"""
        if self.driver is None:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")

            # Configure download directory
            prefs = {
                "download.default_directory": str(self.download_dir.absolute()),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            chrome_options.add_experimental_option("prefs", prefs)

            self.driver = webdriver.Chrome(options=chrome_options)

    def close_driver(self):
        """Close the Selenium driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def wait_for_download(self, timeout: int = 60) -> Optional[Path]:
        """Wait for a file to be downloaded in the download directory"""
        print(f"    Waiting for download to complete...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check for downloaded files (not .crdownload or .tmp)
            files = list(self.download_dir.glob("*"))
            complete_files = [
                f for f in files
                if f.is_file() and not f.name.endswith('.crdownload') and not f.name.endswith('.tmp')
            ]

            if complete_files:
                # Return the most recently modified file
                latest_file = max(complete_files, key=lambda f: f.stat().st_mtime)
                print(f"    Download complete: {latest_file.name}")
                return latest_file

            time.sleep(0.5)

        print(f"    Download timeout after {timeout}s")
        return None

    def generate_digest(self, github_url: str, output_path: Path) -> bool:
        """
        Generate a digest/gist of a GitHub repository using gitingest.com

        Args:
            github_url: Clean GitHub repository URL (e.g., https://github.com/owner/repo)
            output_path: Path where the digest file should be saved

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"  Generating gist via gitingest.com...")
            print(f"    URL: {github_url}")
            print(f"    Output: {output_path.name}")

            # Setup Selenium if not already done
            self.setup_driver()

            # Navigate to gitingest.com
            self.driver.get("https://gitingest.com/")

            # Wait for input field and enter GitHub URL
            input_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "input_text"))
            )
            input_field.clear()
            input_field.send_keys(github_url)

            # Click the Ingest button
            ingest_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            ingest_button.click()

            # Wait for the result page to load and process
            print(f"    Waiting for gitingest to process repository...")

            # Wait for textarea to appear (indicates processing is done)
            try:
                digest_element = WebDriverWait(self.driver, 60).until(
                    EC.presence_of_element_located((By.TAG_NAME, "textarea"))
                )
                print(f"    Processing complete")

                # Give it a moment to fully populate
                time.sleep(2)

                # Clear download directory before downloading
                for f in self.download_dir.glob("*"):
                    if f.is_file():
                        f.unlink()

                # Now click the Download button
                print(f"    Clicking download button...")
                download_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Download')]"))
                )
                download_button.click()

                # Wait for the download to complete
                downloaded_file = self.wait_for_download(timeout=30)

                if downloaded_file and downloaded_file.exists():
                    # Move the downloaded file to the output path
                    shutil.move(str(downloaded_file), str(output_path))

                    file_size_kb = output_path.stat().st_size / 1024
                    print(f"  Success: Gist saved ({file_size_kb:.1f} KB)")
                    return True
                else:
                    print(f"  Failed: Download did not complete")
                    return False

            except Exception as e:
                print(f"  Failed: Could not download gist - {str(e)}")
                return False

        except Exception as e:
            print(f"  Failed: {str(e)}")
            return False

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures driver is closed"""
        self.close_driver()


class GitRepoCrawler:
    """Manages git repository cloning/pulling and gist generation"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(exist_ok=True)
        self.state_file = self.data_dir / "crawl-state.json"
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """Load crawl state from JSON file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠ Warning: Could not load state file: {e}")
                return {}
        return {}

    def _save_state(self):
        """Save crawl state to JSON file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"⚠ Warning: Could not save state file: {e}")

    def extract_repo_info(self, github_url: str) -> Tuple[str, str, str]:
        """
        Extract owner, repo name, and repo identifier from GitHub URL

        Returns:
            Tuple of (owner, repo_name, repo_identifier)
            Example: ('owner', 'repo', 'owner_repo')
        """
        # Clean URL
        url = github_url.strip().rstrip('/')

        # Remove protocol and domain
        if url.startswith('http://') or url.startswith('https://'):
            url = url.split('://', 1)[1]

        if url.startswith('github.com/'):
            url = url.replace('github.com/', '')

        # Split into parts
        parts = url.split('/')
        if len(parts) >= 2:
            owner = parts[0]
            repo_name = parts[1]
            repo_identifier = f"{owner}_{repo_name}"
            return owner, repo_name, repo_identifier

        raise ValueError(f"Invalid GitHub URL format: {github_url}")

    def git_clone_or_pull(self, github_url: str, repo_path: Path) -> bool:
        """
        Clone a repository if it doesn't exist, or pull if it does.

        Returns:
            bool: True if there were changes (new clone or updates), False if no changes
        """
        try:
            if repo_path.exists() and (repo_path / ".git").exists():
                # Repository exists, try to pull
                print(f"  Pulling updates...")

                # Get current HEAD before pull
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                old_commit = result.stdout.strip()

                # Pull updates
                subprocess.run(
                    ["git", "pull", "--ff-only"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )

                # Get new HEAD after pull
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                new_commit = result.stdout.strip()

                if old_commit != new_commit:
                    print(f"  Updates found: {old_commit[:7]} -> {new_commit[:7]}")
                    return True
                else:
                    print(f"  Already up to date")
                    return False

            else:
                # Repository doesn't exist, clone it
                print(f"  Cloning repository...")
                repo_path.parent.mkdir(parents=True, exist_ok=True)

                subprocess.run(
                    ["git", "clone", github_url, str(repo_path)],
                    capture_output=True,
                    text=True,
                    check=True
                )

                print(f"  Clone successful")
                return True

        except subprocess.CalledProcessError as e:
            print(f"  Git operation failed: {e.stderr}")
            return False
        except Exception as e:
            print(f"  Error: {str(e)}")
            return False

    def process_repository(self, github_url: str, gitingest: GitIngestGenerator) -> bool:
        """
        Process a single repository: clone/pull and generate gist if needed

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"\n{'='*70}")
            print(f"Processing: {github_url}")
            print(f"{'='*70}")

            # Extract repository information
            owner, repo_name, repo_identifier = self.extract_repo_info(github_url)

            # Setup paths
            repo_dir = self.data_dir / repo_identifier
            code_dir = repo_dir / "code"
            gist_dir = repo_dir / "gist"
            gist_dir.mkdir(parents=True, exist_ok=True)

            # Clone or pull the repository
            has_changes = self.git_clone_or_pull(github_url, code_dir)

            # Generate gist if there were changes or no gist exists yet
            gist_path = gist_dir / f"{repo_name}_gist.txt"

            if has_changes or not gist_path.exists():
                if not gist_path.exists():
                    print(f"  No existing gist found")

                # Generate new gist
                success = gitingest.generate_digest(github_url, gist_path)

                if success:
                    # Update state
                    self.state[github_url] = {
                        "last_crawled": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "repo_identifier": repo_identifier,
                        "gist_path": str(gist_path),
                        "status": "success"
                    }
                    self._save_state()
                    print(f"  Repository processed successfully")
                    print(f"    Code: {code_dir}")
                    print(f"    Gist: {gist_path}")
                    return True
                else:
                    self.state[github_url] = {
                        "last_crawled": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "status": "failed_gist"
                    }
                    self._save_state()
                    return False
            else:
                print(f"  Skipping gist generation (no changes)")
                return True

        except Exception as e:
            print(f"  Error processing repository: {str(e)}")
            self.state[github_url] = {
                "last_crawled": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "error",
                "error": str(e)
            }
            self._save_state()
            return False


def read_crawl_jobs(jobs_file: Path) -> list:
    """Read GitHub URLs from crawl-jobs.txt"""
    if not jobs_file.exists():
        print(f"Error: {jobs_file} not found")
        print(f"  Create this file with one GitHub URL per line")
        return []

    urls = []
    with open(jobs_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith('#'):
                urls.append(line)

    return urls


def main():
    """Main crawler entry point"""
    print("╔════════════════════════════════════════════════════════════╗")
    print("║         Git Repository Crawler with GitIngest             ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    # Setup paths
    base_dir = Path(__file__).parent
    jobs_file = base_dir / "crawl-jobs.txt"
    data_dir = base_dir / "data"

    # Read crawl jobs
    urls = read_crawl_jobs(jobs_file)

    if not urls:
        print("No URLs to process. Exiting.")
        return

    print(f"Found {len(urls)} repositories to process\n")

    # Initialize crawler and gitingest
    crawler = GitRepoCrawler(data_dir)

    success_count = 0
    failed_count = 0
    skipped_count = 0

    with GitIngestGenerator() as gitingest:
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing repository...")

            result = crawler.process_repository(url, gitingest)

            if result:
                success_count += 1
            else:
                failed_count += 1

    # Print summary
    print(f"\n{'='*70}")
    print("CRAWL SUMMARY")
    print(f"{'='*70}")
    print(f"  Total:   {len(urls)}")
    print(f"  Success: {success_count}")
    print(f"  Failed:  {failed_count}")
    print(f"\nData directory: {data_dir}")
    print(f"State file:     {data_dir / 'crawl-state.json'}")
    print()


if __name__ == "__main__":
    main()
