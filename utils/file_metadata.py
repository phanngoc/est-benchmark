import os
import json
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)

class FileMetadataManager:
    """Quản lý metadata của files để detect duplicates"""

    def __init__(self, uploads_dir: str = "./uploads", metadata_file: str = ".metadata.json"):
        self.uploads_dir = uploads_dir
        self.metadata_path = os.path.join(uploads_dir, metadata_file)
        self.metadata = self.load_metadata()
        logger.debug(f"FileMetadataManager initialized: {self.metadata_path}")

    def load_metadata(self) -> Dict[str, Any]:
        """Load metadata từ file JSON"""
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    logger.info(f"Loaded metadata: {len(metadata)} files tracked")
                    return metadata
            except Exception as e:
                logger.error(f"Failed to load metadata: {str(e)}")
                return {}
        logger.debug("No existing metadata file found, starting fresh")
        return {}

    def save_metadata(self) -> bool:
        """Save metadata vào file JSON"""
        try:
            # Create uploads directory if needed
            os.makedirs(self.uploads_dir, exist_ok=True)

            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved metadata: {len(self.metadata)} files")
            return True
        except Exception as e:
            logger.error(f"Failed to save metadata: {str(e)}")
            return False

    @staticmethod
    def compute_file_hash(file_content: bytes, algorithm: str = "sha256") -> str:
        """
        Compute hash của file content
        Uses hashlib for efficient hashing
        """
        try:
            h = hashlib.new(algorithm)
            h.update(file_content)
            hash_value = h.hexdigest()
            logger.debug(f"Computed {algorithm} hash: {hash_value[:16]}... (length: {len(file_content)} bytes)")
            return hash_value
        except Exception as e:
            logger.error(f"Failed to compute hash: {str(e)}")
            return ""

    def check_duplicate(self, filename: str, file_hash: str, file_size: int) -> Dict[str, Any]:
        """
        Kiểm tra file có duplicate không
        Returns: {
            'is_duplicate': bool,
            'duplicate_type': 'exact'|'content'|'updated'|None,
            'existing_file': str|None,
            'message': str
        }
        """
        result = {
            'is_duplicate': False,
            'duplicate_type': None,
            'existing_file': None,
            'message': ''
        }

        # Check if filename exists
        if filename in self.metadata:
            existing = self.metadata[filename]
            if existing['hash'] == file_hash:
                # Exact duplicate: same filename, same content
                result['is_duplicate'] = True
                result['duplicate_type'] = 'exact'
                result['existing_file'] = filename
                result['message'] = f"File đã tồn tại với nội dung giống hệt (uploaded {existing['uploaded_at']})"
                logger.info(f"Exact duplicate detected: {filename}")
                return result
            else:
                # Content updated: same filename, different content
                result['is_duplicate'] = False
                result['duplicate_type'] = 'updated'
                result['existing_file'] = filename
                result['message'] = f"File đã tồn tại nhưng nội dung khác (sẽ update)"
                logger.info(f"Updated file detected: {filename}")
                return result

        # Check if hash exists with different filename
        for existing_filename, existing_data in self.metadata.items():
            if existing_data['hash'] == file_hash:
                # Content duplicate: different filename, same content
                result['is_duplicate'] = True
                result['duplicate_type'] = 'content'
                result['existing_file'] = existing_filename
                result['message'] = f"Nội dung giống với file '{existing_filename}' (uploaded {existing_data['uploaded_at']})"
                logger.info(f"Content duplicate detected: {filename} matches {existing_filename}")
                return result

        # New file
        result['message'] = "File mới"
        logger.debug(f"New file detected: {filename}")
        return result

    def add_file(self, filename: str, file_hash: str, file_size: int, processed: bool = True) -> bool:
        """Thêm hoặc update file metadata"""
        try:
            self.metadata[filename] = {
                'hash': file_hash,
                'size_bytes': file_size,
                'uploaded_at': datetime.now().isoformat(),
                'processed': processed
            }
            logger.info(f"Added/updated metadata for: {filename}")
            return self.save_metadata()
        except Exception as e:
            logger.error(f"Failed to add file metadata: {str(e)}")
            return False

    def remove_file(self, filename: str) -> bool:
        """Xóa file metadata"""
        try:
            if filename in self.metadata:
                del self.metadata[filename]
                logger.info(f"Removed metadata for: {filename}")
                return self.save_metadata()
            return True
        except Exception as e:
            logger.error(f"Failed to remove file metadata: {str(e)}")
            return False

    def get_file_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """Lấy thông tin metadata của file"""
        return self.metadata.get(filename)

    def get_stats(self) -> Dict[str, Any]:
        """Lấy thống kê metadata"""
        return {
            'total_files': len(self.metadata),
            'total_size': sum(f['size_bytes'] for f in self.metadata.values()),
            'files': list(self.metadata.keys())
        }
