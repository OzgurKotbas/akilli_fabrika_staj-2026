# -*- coding: utf-8 -*-
import yaml
import os
import re
from pathlib import Path

try:
    from dotenv import load_dotenv
    # Proje kök dizinindeki .env dosyasını yükle
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass

# Proje kök dizini (bu dosyanın 3 üst dizini: scripts/core/config_okuyucu.py -> scripts/core -> scripts -> kök)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

def resolve_env_vars(text: str) -> str:
    """Metin içindeki ${VAR:-default} ve ${VAR} desenlerini os.environ ile çözer."""
    pattern = re.compile(r'\$\{([^}^{]+)\}')
    
    def replacer(match):
        inner = match.group(1)
        if ':-' in inner:
            var_name, default_val = inner.split(':-', 1)
            return os.environ.get(var_name, default_val)
        else:
            return os.environ.get(inner, '')
            
    return pattern.sub(replacer, text)

def load_config():
    """config.yaml dosyasını okur, env varları çözer ve dict olarak döner."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Yapılandırma dosyası bulunamadı: {CONFIG_PATH}")
    
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        
    resolved_content = resolve_env_vars(content)
    config = yaml.safe_load(resolved_content)
    return config

def get_path(config_path_key):
    """
    Config içindeki 'paths' altından okunan göreceli yolları 
    mutlak (absolute) Path objesine dönüştürür.
    Kullanım: get_path(config['paths']['default_engel_video'])
    """
    if not config_path_key:
        return None
    return PROJECT_ROOT / config_path_key

# Modül import edildiğinde varsayılan config yüklenir
try:
    CONFIG = load_config()
except Exception as e:
    print(f"[UYARI] config_okuyucu.py başlatılamadı: {e}")
    CONFIG = {}
