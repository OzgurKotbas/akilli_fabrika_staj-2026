# -*- coding: utf-8 -*-
import yaml
from pathlib import Path

# Proje kök dizini (bu dosyanın 3 üst dizini: scripts/core/config_okuyucu.py -> scripts/core -> scripts -> kök)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

def load_config():
    """config.yaml dosyasını okur ve sözlük (dict) olarak döner."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Yapılandırma dosyası bulunamadı: {CONFIG_PATH}")
    
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
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
