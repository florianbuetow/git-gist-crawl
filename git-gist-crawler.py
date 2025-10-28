#!/usr/bin/env python3
"""
Git Repository Crawler with GitIngest Integration

Clones/pulls GitHub repositories and generates gists using gitingest.com
"""

import os
import subprocess
import time
import logging
from pathlib import Path
from typing import Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import shutil
import json


def setup_logging(data_dir: Path) -> logging.Logger:
    """
    Configure logging to write to data/crawl.log
    Format: yyyy-mm-dd HH:MM:SS | [loglevel] | Log message
    """
    # Ensure data directory exists
    data_dir.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger('git-gist-crawler')
    logger.setLevel(logging.INFO)

    # Remove any existing handlers
    logger.handlers = []

    # Create file handler
    log_file = data_dir / 'crawl.log'
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s | [%(levelname)s] | %(message)s',
                                 datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(file_handler)

    return logger


class GitIngestGenerator:
    """Generate repository digests using gitingest.com"""

    def __init__(self, logger: logging.Logger, download_dir: Optional[Path] = None):
        self.logger = logger
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
        """
        Wait for a file to be downloaded in the download directory.
        Handles both standard Chrome downloads and Alpine Chromium downloads
        (which may use .org.chromium.Chromium.* naming pattern).
        """
        self.logger.info("Waiting for download to complete...")

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
                # This handles both standard downloads and Alpine Chromium's .org.chromium.Chromium.* files
                latest_file = max(complete_files, key=lambda f: f.stat().st_mtime)
                self.logger.info(f"Download complete: {latest_file.name}")
                return latest_file

            time.sleep(0.5)

        self.logger.warning(f"Download timeout after {timeout}s")
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
            print(f"  Creating gist via gitingest.com...")
            self.logger.info("Generating gist via gitingest.com...")
            self.logger.info(f"URL: {github_url}")
            self.logger.info(f"Output: {output_path.name}")

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
            self.logger.info("Waiting for gitingest to process repository...")

            # Wait for textarea to appear (indicates processing is done)
            try:
                digest_element = WebDriverWait(self.driver, 60).until(
                    EC.presence_of_element_located((By.TAG_NAME, "textarea"))
                )
                self.logger.info("Processing complete")

                # Give it a moment to fully populate
                time.sleep(2)

                # Clear download directory before downloading
                for f in self.download_dir.glob("*"):
                    if f.is_file():
                        f.unlink()

                # Now click the Download button
                self.logger.info("Clicking download button...")
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
                    print(f"  Gist saved successfully ({file_size_kb:.1f} KB)")
                    self.logger.info(f"Success: Gist saved ({file_size_kb:.1f} KB)")
                    return True
                else:
                    print(f"  Failed: Download did not complete")
                    self.logger.error("Failed: Download did not complete")
                    return False

            except Exception as e:
                print(f"  Failed: Could not download gist - {str(e)}")
                self.logger.error(f"Failed: Could not download gist - {str(e)}")
                return False

        except Exception as e:
            print(f"  Failed: {str(e)}")
            self.logger.error(f"Failed: {str(e)}")
            return False

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures driver is closed"""
        self.close_driver()


class GitRepoCrawler:
    """Manages git repository cloning/pulling and gist generation"""

    def __init__(self, logger: logging.Logger, data_dir: Path):
        self.logger = logger
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
                self.logger.warning(f"Could not load state file: {e}")
                return {}
        return {}

    def _save_state(self):
        """Save crawl state to JSON file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Could not save state file: {e}")

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
        Cleans up corrupted/partial repositories on failure.

        Returns:
            bool: True if there were changes (new clone or updates), False if no changes
        """
        try:
            if repo_path.exists() and (repo_path / ".git").exists():
                # Repository exists, try to pull
                print(f"  Pulling updates...")
                self.logger.info("Pulling updates...")

                try:
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
                        self.logger.info(f"Updates found: {old_commit[:7]} -> {new_commit[:7]}")
                        return True
                    else:
                        print(f"  Already up to date")
                        self.logger.info("Already up to date")
                        return False

                except subprocess.CalledProcessError as e:
                    # Git pull failed - repo might be corrupted
                    print(f"  Repository corrupted, cleaning up for re-clone...")
                    self.logger.warning(f"Git pull failed, removing corrupted repo: {e.stderr}")
                    shutil.rmtree(repo_path, ignore_errors=True)

                    # Fall through to clone
                    print(f"  Cloning repository: {github_url}")
                    self.logger.info("Cloning repository after cleanup...")
                    repo_path.parent.mkdir(parents=True, exist_ok=True)

                    subprocess.run(
                        ["git", "clone", github_url, str(repo_path)],
                        capture_output=True,
                        text=True,
                        check=True
                    )

                    print(f"  Clone successful")
                    self.logger.info("Clone successful")
                    return True

            else:
                # Repository doesn't exist or .git is missing, clone it
                # Clean up any partial directory first
                if repo_path.exists():
                    print(f"  Removing incomplete repository...")
                    self.logger.info("Removing incomplete repository directory...")
                    shutil.rmtree(repo_path, ignore_errors=True)

                print(f"  Cloning repository: {github_url}")
                self.logger.info("Cloning repository...")
                repo_path.parent.mkdir(parents=True, exist_ok=True)

                try:
                    subprocess.run(
                        ["git", "clone", github_url, str(repo_path)],
                        capture_output=True,
                        text=True,
                        check=True
                    )

                    print(f"  Clone successful")
                    self.logger.info("Clone successful")
                    return True

                except subprocess.CalledProcessError as e:
                    # Clone failed - clean up partial directory
                    print(f"  Clone failed, cleaning up...")
                    self.logger.error(f"Git clone failed: {e.stderr}")
                    if repo_path.exists():
                        shutil.rmtree(repo_path, ignore_errors=True)
                        self.logger.info("Cleaned up partial clone directory")
                    return False

        except Exception as e:
            print(f"  Error: {str(e)}")
            self.logger.error(f"Error: {str(e)}")
            # Clean up on unexpected errors
            if repo_path.exists() and not (repo_path / ".git").exists():
                shutil.rmtree(repo_path, ignore_errors=True)
                self.logger.info("Cleaned up after error")
            return False

    def process_repository(self, github_url: str, gitingest: GitIngestGenerator) -> bool:
        """
        Process a single repository: clone/pull and generate gist if needed.
        Uses state flags (clone_success, gist_success) to track progress.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"\n{'='*70}")
            print(f"Processing: {github_url}")
            print(f"{'='*70}")

            self.logger.info("="*70)
            self.logger.info(f"Processing: {github_url}")
            self.logger.info("="*70)

            # Extract repository information
            owner, repo_name, repo_identifier = self.extract_repo_info(github_url)

            # Setup paths
            repo_dir = self.data_dir / repo_identifier
            code_dir = repo_dir / "code"
            gist_dir = repo_dir / "gist"
            gist_dir.mkdir(parents=True, exist_ok=True)
            gist_path = gist_dir / f"{repo_name}_gist.txt"

            # Get current state
            current_state = self.state.get(github_url, {})
            clone_success = current_state.get("clone_success", False)
            gist_success = current_state.get("gist_success", False)

            # Clone or pull the repository
            # Will attempt if clone_success is False or if repo exists (to pull updates)
            has_changes = self.git_clone_or_pull(github_url, code_dir)

            # Update clone success flag
            clone_successful = (code_dir / ".git").exists()

            if not clone_successful:
                # Clone failed completely
                self.state[github_url] = {
                    "clone_success": False,
                    "gist_success": False
                }
                self._save_state()
                return False

            # Generate gist if:
            # 1. Clone just succeeded for the first time
            # 2. Repository had changes (new commits)
            # 3. OR previous gist generation failed (gist_success = False)
            need_gist = has_changes or not gist_success

            if need_gist:
                if not gist_success:
                    print(f"  Previous gist generation failed or missing, will create")
                    self.logger.info("Previous gist generation failed or missing")
                elif has_changes:
                    print(f"  Repository changed, regenerating gist")
                    self.logger.info("Repository changed, regenerating gist")

                # Generate new gist
                gist_gen_success = gitingest.generate_digest(github_url, gist_path)

                # Update state with both flags
                self.state[github_url] = {
                    "clone_success": True,
                    "gist_success": gist_gen_success
                }
                self._save_state()

                if gist_gen_success:
                    self.logger.info("Repository processed successfully")
                    self.logger.info(f"Code: {code_dir}")
                    self.logger.info(f"Gist: {gist_path}")
                    return True
                else:
                    return False
            else:
                print(f"  Skipping gist generation (no changes, gist exists)")
                self.logger.info("Skipping gist generation (no changes, gist exists)")
                # State already has both flags set to True, no need to update
                return True

        except Exception as e:
            print(f"  Error processing repository: {str(e)}")
            self.logger.error(f"Error processing repository: {str(e)}")
            self.state[github_url] = {
                "clone_success": False,
                "gist_success": False
            }
            self._save_state()
            return False


def read_crawl_jobs(logger: logging.Logger, jobs_file: Path) -> list:
    """Read GitHub URLs from crawl-jobs.txt"""
    if not jobs_file.exists():
        logger.error(f"Error: {jobs_file} not found")
        logger.error("Create this file with one GitHub URL per line")
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
    # Setup paths first
    base_dir = Path(__file__).parent
    jobs_file = base_dir / "crawl-jobs.txt"
    data_dir = base_dir / "data"

    # Setup logging
    logger = setup_logging(data_dir)

    # Print header to console
    print("╔════════════════════════════════════════════════════════════╗")
    print("║         Git Repository Crawler with GitIngest             ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    logger.info("="*70)
    logger.info("Git Repository Crawler with GitIngest")
    logger.info("="*70)

    # Read crawl jobs
    urls = read_crawl_jobs(logger, jobs_file)

    if not urls:
        logger.error("No URLs to process. Exiting.")
        print("No URLs to process. Exiting.")
        return

    print(f"Found {len(urls)} repositories to process\n")
    logger.info(f"Found {len(urls)} repositories to process")

    # Initialize crawler and gitingest
    crawler = GitRepoCrawler(logger, data_dir)

    success_count = 0
    failed_count = 0

    with GitIngestGenerator(logger) as gitingest:
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing repository...")
            logger.info(f"[{i}/{len(urls)}] Processing repository...")

            result = crawler.process_repository(url, gitingest)

            if result:
                success_count += 1
            else:
                failed_count += 1

    # Print summary to console and log
    print(f"\n{'='*70}")
    print("CRAWL SUMMARY")
    print(f"{'='*70}")
    print(f"  Total:   {len(urls)}")
    print(f"  Success: {success_count}")
    print(f"  Failed:  {failed_count}")
    print(f"\nData directory: {data_dir}")
    print(f"State file:     {data_dir / 'crawl-state.json'}")
    print()

    logger.info("="*70)
    logger.info("CRAWL SUMMARY")
    logger.info("="*70)
    logger.info(f"Total:   {len(urls)}")
    logger.info(f"Success: {success_count}")
    logger.info(f"Failed:  {failed_count}")
    logger.info(f"Data directory: {data_dir}")
    logger.info(f"State file: {data_dir / 'crawl-state.json'}")


if __name__ == "__main__":
    main()
