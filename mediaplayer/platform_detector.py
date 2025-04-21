#!/usr/bin/env python3
"""
Rileva caratteristiche specifiche della piattaforma per ottimizzare il rendering.
Supporta Alpine Linux, iSH, Android, e altri ambienti minimali.
"""

import os
import sys
import platform
import subprocess

def detect_platform():
    """
    Rileva e restituisce informazioni dettagliate sulla piattaforma corrente.
    Utile per personalizzare il comportamento su diversi sistemi.
    """
    info = {
        'system': platform.system().lower(),
        'release': platform.release(),
        'machine': platform.machine().lower(),
        'python_version': platform.python_version(),
        'implementation': platform.python_implementation(),
        'is_64bit': sys.maxsize > 2**32,
        'terminal_size': os.get_terminal_size() if hasattr(os, 'get_terminal_size') else (80, 24),
    }
    
    # Potrebbe essere un ambiente mobile?
    info['is_arm'] = 'arm' in info['machine'] or 'aarch' in info['machine']
    
    # Rilevamento Alpine Linux (MUSL)
    info['is_alpine'] = os.path.exists('/etc/alpine-release')
    
    # Rilevamento iSH
    info['is_ish'] = False
    if os.path.exists('/proc/version'):
        try:
            with open('/proc/version', 'r') as f:
                version_info = f.read().lower()
                info['is_ish'] = 'ish' in version_info
        except:
            pass
            
    # Rilevamento Termux/Android
    info['is_termux'] = 'com.termux' in os.environ.get('PREFIX', '')
    info['is_android'] = os.environ.get('ANDROID_DATA', '') != ''
    
    # Rilevamento iOS (approssimativo)
    info['is_ios'] = 'ios' in platform.version().lower() or 'iphone' in platform.version().lower()
    
    # Rilevamento WSL
    info['is_wsl'] = False
    if info['system'] == 'linux':
        if os.path.exists('/proc/version'):
            try:
                with open('/proc/version', 'r') as f:
                    version_info = f.read().lower()
                    info['is_wsl'] = 'microsoft' in version_info or 'wsl' in version_info
            except:
                pass
    
    # Ottimizzazioni suggerite
    info['use_simple_rendering'] = info['is_alpine'] or info['is_ish'] or info['is_termux']
    info['is_limited_terminal'] = info['is_alpine'] or info['is_ish'] or info['use_simple_rendering']
    info['max_fps'] = 12 if info['is_limited_terminal'] else 24
    
    return info

def get_optimal_rendering_settings():
    """
    Restituisce impostazioni di rendering ottimali per la piattaforma corrente.
    Utile per regolare automaticamente qualità e prestazioni.
    """
    platform_info = detect_platform()
    
    settings = {
        'use_unicode_blocks': True,
        'use_256_colors': True,
        'use_animations': True,
        'max_fps': 24,
        'buffer_size': 10,
        'target_width_ratio': 1.0,
        'target_height_ratio': 1.0,
        'use_prerender': False,  # Nuova opzione per pre-rendering
    }
    
    # Adatta le impostazioni alla piattaforma
    if platform_info['is_limited_terminal']:
        settings['max_fps'] = 12
        settings['buffer_size'] = 5
        settings['use_prerender'] = True  # Abilita pre-rendering su terminali limitati
        
        # Per iSH/Alpine, che possono avere problemi con Unicode o colori
        if platform_info['is_alpine'] or platform_info['is_ish']:
            settings['use_animations'] = False
            settings['target_width_ratio'] = 0.8  # Riduce dimensioni per migliori performance
    
    # Ottimizzazioni per dispositivi mobili
    if platform_info['is_arm'] or platform_info['is_android'] or platform_info['is_ios'] or platform_info['is_termux']:
        settings['target_width_ratio'] = 0.8
        settings['target_height_ratio'] = 0.9
        settings['use_prerender'] = True  # Abilita pre-rendering su dispositivi mobili
    
    return settings

if __name__ == "__main__":
    """Se eseguito direttamente, mostra informazioni sulla piattaforma corrente."""
    platform_info = detect_platform()
    
    print("Informazioni piattaforma:")
    for key, value in platform_info.items():
        print(f"  {key}: {value}")
    
    print("\nImpostazioni di rendering ottimali:")
    settings = get_optimal_rendering_settings()
    for key, value in settings.items():
        print(f"  {key}: {value}")
