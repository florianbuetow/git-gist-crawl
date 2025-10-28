# Git Gist Crawl

Automated GitHub repository crawler to generate LLM context data. It generates comprehensive gists using gitingest.com. Clones repos, tracks changes, and regenerates gists only when updates are detected.

## Features

- **Smart Updates**: Only regenerates gists when repository changes are detected via git pull
- **Batch Processing**: Process multiple repositories from a queue file
- **State Tracking**: Maintains crawl history with success flags for cloning and gist generation
- **Error Handling**: Automatic cleanup of corrupted repos and retry on next run
- **Logging**: Detailed logging to `data/crawl.log` with console output for key progress
- **Docker Support**: Optional containerized execution with Alpine Linux
- **Organized Storage**: Clean directory structure separating cloned code and generated gists

## Requirements

### Local Execution
- Python 3.10+
- `uv` package manager
- Git
- Google Chrome

### Docker Execution (Optional)
- Docker
- No other dependencies needed (all included in container)

## Installation

```bash
make init
```

This will:
- Install Python dependencies (selenium)
- Create the data directory

## Usage

### 1. Add Repositories to Queue

Edit `crawl-jobs.txt` and add GitHub repository URLs (one per line):

```
https://github.com/coderamp-labs/gitingest
https://github.com/anthropics/anthropic-sdk-python
```

Lines starting with `#` are comments and will be ignored.

### 2. Run Crawler

```bash
make crawl
```

The crawler will:
- Clone repositories to `data/[owner_repo]/code/`
- Generate gists to `data/[owner_repo]/gist/[repo]_gist.txt`
- Track state in `data/crawl-state.json`

### 3. Purge Data

```bash
make purge
```

Removes all crawled data and state files.

## Directory Structure

```
gist-crawl/
├── .gitignore                    # Git ignore rules
├── crawl-jobs.txt                # Queue of repositories to crawl
├── data/                         # Crawl output directory
│   ├── crawl.log                 # Detailed execution log
│   ├── crawl-state.json          # State tracking with success flags
│   └── [owner_repo]/             # Per-repository directory
│       ├── code/                 # Git clone of repository
│       └── gist/                 # Generated gist files
│           └── [repo]_gist.txt   # Repository gist
├── Dockerfile                    # Alpine-based Docker image
├── git-gist-crawler.py           # Main crawler script
├── Makefile                      # Build automation
├── pyproject.toml                # Python dependencies
├── README.md                     # This file
└── uv.lock                       # Dependency lock file
```

## Make Targets

```bash
make help            # Show available targets
make init            # Install dependencies
make crawl           # Run crawler (auto-runs init if needed)
make purge           # Remove all data, state, and Docker image
make docker          # Build and run in Docker container
make docker-rebuild  # Force rebuild Docker image without cache
make docker-delete   # Remove Docker image
```

## How It Works

### Smart Update Behavior

1. **First Run**: Clones repository and generates gist
2. **Subsequent Runs**:
   - Runs `git pull` to check for updates
   - If commit SHA changed: Regenerates gist
   - If no changes: Skips gist generation
3. **Missing Gist**: Regenerates even if repository unchanged

This minimizes unnecessary gitingest.com requests and processing time.

### Gist Generation

The crawler uses [gitingest.com](https://gitingest.com/) via Selenium to generate comprehensive repository gists containing:
- Repository structure
- File contents
- Metadata

These gists are ideal for:
- LLM context ingestion
- Code analysis
- Documentation generation
- Repository summaries

## Example Workflow

### Local Execution

```bash
# First time setup
make init

# Add repositories to crawl-jobs.txt
echo "https://github.com/coderamp-labs/gitingest" >> crawl-jobs.txt

# Run crawler
make crawl

# View generated gist
cat data/coderamp-labs_gitingest/gist/gitingest_gist.txt

# View logs
cat data/crawl.log

# Clean up everything
make purge
```

### Docker Execution

```bash
# Add repositories to crawl-jobs.txt
echo "https://github.com/coderamp-labs/gitingest" >> crawl-jobs.txt

# Run crawler in Docker (builds image if needed)
make docker

# View generated gist
cat data/coderamp-labs_gitingest/gist/gitingest_gist.txt

# Rebuild Docker image without cache
make docker-rebuild

# Clean up everything (including Docker image)
make purge
```

## State Tracking

The `data/crawl-state.json` file tracks success status for each repository:

```json
{
  "https://github.com/owner/repo": {
    "clone_success": true,
    "gist_success": true
  }
}
```

The crawler automatically retries failed operations on subsequent runs. Both clone and gist generation must succeed for a repository to be considered complete.

## Logging

Detailed logs are written to `data/crawl.log` with timestamps and log levels. Key progress is also displayed on the console for easy monitoring.

## Error Handling

The crawler includes automatic error handling and recovery. Corrupted repositories are detected and cleaned up automatically. Failed operations are tracked in state and retried on subsequent runs. All operations are atomic to prevent partial or inconsistent data.

## Troubleshooting

**Chrome Not Found**: Ensure Google Chrome is installed. Selenium will automatically download and manage ChromeDriver.

**Git Authentication**: For private repositories, configure credentials with `git config --global credential.helper store`

**Timeouts**: Large repositories may timeout. Modify the timeout in `git-gist-crawler.py` if needed.

**Docker Issues**: If the container fails, try `make docker-rebuild` to force a fresh build.

## Limitations

This project uses Selenium to automate the [gitingest.com](https://gitingest.com/) website for gist generation. This approach has limitations:

- **Fragile**: Gist generation will break if the website UI changes
- **Slower**: Browser automation adds overhead compared to direct API calls
- **Less Robust**: No native error handling or rate limiting

### Recommended Alternative

For a more robust implementation, use the [gitingest Python library](https://github.com/coderamp-labs/gitingest) directly with proper GitHub API authentication. This would provide:
- Direct API access without browser automation
- Better error handling and rate limiting
- No dependency on website UI stability
- Faster processing
