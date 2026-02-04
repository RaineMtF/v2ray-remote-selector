import os
import json
import uuid
import shutil
import subprocess
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("executor")

def run_python_provider(provider, base_dir):
    name = provider.get("name")
    script_name = provider.get("script")
    requirements = provider.get("requirements", [])
    configs = provider.get("config", {})
    output_target = provider.get("output")
    url = provider.get("url")

    logger.info(f"Processing Python provider: {name} ({url})")

    # 1. Create temp directory
    u_id = str(uuid.uuid4())
    temp_dir = Path(base_dir) / "temp" / u_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created temp directory: {temp_dir}")

    try:
        # 2. Copy script
        provider_script_path = Path(base_dir) / "scripts" / "provider" / script_name
        if not provider_script_path.exists():
            logger.error(f"Script not found: {provider_script_path}")
            return

        shutil.copy(provider_script_path, temp_dir / script_name)
        logger.info(f"Copied script to {temp_dir / script_name}")

        # 3. Create venv
        venv_dir = temp_dir / "venv"
        logger.info("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

        # Determine venv executable path
        if os.name == 'nt':
            python_exe = venv_dir / "Scripts" / "python.exe"
            pip_exe = venv_dir / "Scripts" / "pip.exe"
        else:
            python_exe = venv_dir / "bin" / "python"
            pip_exe = venv_dir / "bin" / "pip"

        # 4. Install requirements
        subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"] + requirements, check=True)
        if requirements:
            logger.info(f"Installing requirements: {', '.join(requirements)}")
            subprocess.run([str(pip_exe), "install"] + requirements, check=True)

        # 5. Generate config files
        for filename, content in configs.items():
            ext = Path(filename).suffix.lower()
            if ext in ['.json', '.yml', '.yaml', '.toml']:
                config_path = temp_dir / filename
                with open(config_path, 'w', encoding='utf-8') as f:
                    if ext == '.json':
                        json.dump(content, f, indent=4)
                    elif ext in ['.yml', '.yaml']:
                        import yaml
                        yaml.dump(content, f)
                    elif ext == '.toml':
                        import toml
                        toml.dump(content, f)
                logger.info(f"Generated config file: {filename}")
            else:
                logger.warning(f"Unsupported config format: {filename}")

        # 6. Execute script
        logger.info(f"Executing script: {script_name}")
        subprocess.run([str(python_exe), script_name], cwd=temp_dir, check=True)

        # 7. Move output to config folder
        source_output = temp_dir / output_target
        if source_output.exists():
            config_dir = Path(base_dir) / "config"
            config_dir.mkdir(exist_ok=True)
            
            output_ext = Path(output_target).suffix
            final_name = f"{name}{output_ext}"
            final_path = config_dir / final_name
            
            shutil.copy(source_output, final_path)
            logger.info(f"Output saved to: {final_path}")
        else:
            logger.error(f"Output file not found after execution: {output_target}")

    except Exception as e:
        logger.error(f"Failed to process {name}: {str(e)}")
    finally:
        # Cleanup temp directory
        # shutil.rmtree(temp_dir)
        # logger.info(f"Cleaned up temp directory: {temp_dir}")
        pass

def run_merge(merge_config, base_dir):
    logger.info("Starting file merge process...")
    config_dir = Path(base_dir) / "config"
    if not config_dir.exists():
        logger.error(f"Config directory not found: {config_dir}")
        return

    for output_filename, input_filenames in merge_config.items():
        logger.info(f"Merging into {output_filename}")
        merged_content = ""
        for input_filename in input_filenames:
            input_path = config_dir / input_filename
            if input_path.exists():
                logger.info(f"Reading {input_filename}")
                with open(input_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    merged_content += content + "\n\n"
            else:
                logger.warning(f"File not found for merge: {input_filename}")
        
        output_path = config_dir / output_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(merged_content)
        logger.info(f"Merged file created: {output_path}")

import argparse

def main():
    parser = argparse.ArgumentParser(description="Execute providers.")
    parser.add_argument("--type", choices=["python", "node", "merge"], required=True, help="Type of providers to run")
    parser.add_argument("--force", action="store_true", help="Force run all providers")
    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent.absolute()
    config_path = base_dir / "config.json"

    if not config_path.exists():
        logger.error("config.json not found")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)

    if args.type == "python":
        providers = config_data.get("python", [])
        for provider in providers:
            if provider.get("enable", True) or args.force:
                run_python_provider(provider, base_dir)
    elif args.type == "merge":
        merge_config = config_data.get("merge", {})
        if merge_config:
            run_merge(merge_config, base_dir)
        else:
            logger.info("No merge configuration found.")

if __name__ == "__main__":
    main()
