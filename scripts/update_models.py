#!/usr/bin/env python3
"""
NEXUS Model Update Script
Downloads and updates AI models for NEXUS platform
"""

import os
import sys
import requests
from pathlib import Path
from tqdm import tqdm

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nexus.config import settings
from nexus.utils.logger import logger


class ModelUpdater:
    """Handles downloading and updating AI models"""

    def __init__(self):
        self.models_dir = Path("models")
        self.models_dir.mkdir(exist_ok=True)

    def download_file(self, url: str, destination: Path) -> bool:
        """Download file with progress bar"""
        try:
            logger.info(f"Downloading {url}")
            
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            
            with destination.open('wb') as f, tqdm(
                desc=destination.name,
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
            
            logger.info(f"Successfully downloaded {destination}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return False

    def download_llama_model(self):
        """Download LLaMA model"""
        # List of available LLaMA models
        models = {
            "Llama-3.2-1B-Instruct-Q4_K_M": "https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct/resolve/main/consolidated.00.pth",  # Placeholder URL
            # Add more models as they become available
        }
        
        print("\nAvailable LLaMA Models:")
        for i, model_name in enumerate(models.keys(), 1):
            print(f"{i}. {model_name}")
        
        print(f"{len(models) + 1}. All models")
        print("0. Cancel")
        
        choice = input("\nSelect model to download (number): ").strip()
        
        if choice == "0":
            logger.info("Download cancelled")
            return False
        
        try:
            choice_idx = int(choice) - 1
            
            if choice_idx < 0:
                logger.info("Download cancelled")
                return False
            
            if choice_idx < len(models):
                model_name = list(models.keys())[choice_idx]
                url = models[model_name]
                destination = self.models_dir / f"{model_name}.gguf"
                
                return self.download_file(url, destination)
            elif choice_idx == len(models):
                # Download all models
                success = True
                for model_name, url in models.items():
                    destination = self.models_dir / f"{model_name}.gguf"
                    if not self.download_file(url, destination):
                        success = False
                return success
            else:
                logger.error("Invalid choice")
                return False
                
        except ValueError:
            logger.error("Invalid input")
            return False

    def update_embeddings_model(self):
        """Update sentence transformer embeddings model"""
        try:
            from sentence_transformers import SentenceTransformer
            
            print("\nAvailable embedding models:")
            models = [
                "all-MiniLM-L6-v2 (Fast, Recommended)",
                "all-mpnet-base-v2 (Better Quality)",
                "paraphrase-multilingual-MiniLM-L12-v2 (Multilingual)"
            ]
            
            for i, model in enumerate(models, 1):
                print(f"{i}. {model}")
            
            print("0. Cancel")
            
            choice = input("\nSelect model to download (number): ").strip()
            
            if choice == "0":
                logger.info("Download cancelled")
                return False
            
            try:
                choice_idx = int(choice) - 1
                
                if choice_idx < 0:
                    logger.info("Download cancelled")
                    return False
                
                if choice_idx < len(models):
                    model_name = models[choice_idx].split()[0]
                    
                    logger.info(f"Downloading {model_name}...")
                    model = SentenceTransformer(model_name)
                    model.save(str(self.models_dir / model_name))
                    
                    logger.info(f"Successfully downloaded {model_name}")
                    return True
                else:
                    logger.error("Invalid choice")
                    return False
                    
            except ValueError:
                logger.error("Invalid input")
                return False
                
        except Exception as e:
            logger.error(f"Failed to download embeddings model: {e}")
            return False

    def list_installed_models(self):
        """List currently installed models"""
        print("\nInstalled Models:")
        print("=" * 60)
        
        # LLaMA models
        llama_models = list(self.models_dir.glob("*.gguf"))
        if llama_models:
            print("\nLLaMA Models:")
            for model in llama_models:
                size_mb = model.stat().st_size / (1024 * 1024)
                print(f"  {model.name} ({size_mb:.1f} MB)")
        else:
            print("\nLLaMA Models: None installed")
        
        # Embedding models
        embedding_models = list(self.models_dir.glob("*"))
        if embedding_models:
            print("\nEmbedding Models:")
            for model_dir in self.models_dir.iterdir():
                if model_dir.is_dir() and model_dir.name not in [".", ".."]:
                    print(f"  {model_dir.name}")
        else:
            print("\nEmbedding Models: None installed")
        
        print("=" * 60)

    def cleanup_old_models(self):
        """Remove old or unused models"""
        print("\nInstalled Models:")
        print("=" * 60)
        
        models = []
        for model_path in self.models_dir.glob("*"):
            if model_path.is_file():
                size_mb = model_path.stat().st_size / (1024 * 1024)
                models.append((model_path, size_mb))
                print(f"{len(models)}. {model_path.name} ({size_mb:.1f} MB)")
        
        print("0. Cancel")
        
        choice = input("\nSelect model to remove (number): ").strip()
        
        if choice == "0":
            logger.info("Cleanup cancelled")
            return False
        
        try:
            choice_idx = int(choice) - 1
            
            if choice_idx < 0:
                logger.info("Cleanup cancelled")
                return False
            
            if 0 <= choice_idx < len(models):
                model_path, _ = models[choice_idx]
                
                confirm = input(f"Are you sure you want to delete {model_path.name}? (y/N): ").strip().lower()
                
                if confirm == 'y':
                    model_path.unlink()
                    logger.info(f"Deleted {model_path.name}")
                    return True
                else:
                    logger.info("Delete cancelled")
                    return False
            else:
                logger.error("Invalid choice")
                return False
                
        except ValueError:
            logger.error("Invalid input")
            return False

    def run(self):
        """Main update menu"""
        print("\n" + "=" * 60)
        print("NEXUS Model Updater")
        print("=" * 60)
        
        while True:
            print("\nOptions:")
            print("1. Download LLaMA model")
            print("2. Update embeddings model")
            print("3. List installed models")
            print("4. Cleanup old models")
            print("5. Check model compatibility")
            print("0. Exit")
            
            choice = input("\nSelect option (0-5): ").strip()
            
            if choice == "0":
                logger.info("Exiting...")
                break
            elif choice == "1":
                self.download_llama_model()
            elif choice == "2":
                self.update_embeddings_model()
            elif choice == "3":
                self.list_installed_models()
            elif choice == "4":
                self.cleanup_old_models()
            elif choice == "5":
                self.check_compatibility()
            else:
                logger.error("Invalid choice")

    def check_compatibility(self):
        """Check model compatibility with current setup"""
        print("\nModel Compatibility Check")
        print("=" * 60)
        
        # Check Python version
        python_version = sys.version_info
        print(f"Python Version: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        if python_version >= (3, 11):
            print("✅ Python version compatible")
        else:
            print("❌ Python 3.11+ required")
        
        # Check llama-cpp-python
        try:
            import llama_cpp
            print(f"✅ llama-cpp-python: {llama_cpp.__version__}")
        except ImportError:
            print("❌ llama-cpp-python not installed")
        
        # Check sentence-transformers
        try:
            import sentence_transformers
            print(f"✅ sentence-transformers: {sentence_transformers.__version__}")
        except ImportError:
            print("❌ sentence-transformers not installed")
        
        # Check models directory
        if self.models_dir.exists():
            print(f"✅ Models directory: {self.models_dir}")
            models_count = len(list(self.models_dir.glob("*")))
            print(f"   {models_count} models installed")
        else:
            print("❌ Models directory not found")
        
        # Check disk space
        disk_usage = self.models_dir.statvfs(self.models_dir)
        free_gb = (disk_usage.f_fravail * disk_usage.f_frsize) / (1024 ** 3)
        print(f"💾 Available disk space: {free_gb:.1f} GB")
        
        print("=" * 60)


if __name__ == "__main__":
    updater = ModelUpdater()
    updater.run()