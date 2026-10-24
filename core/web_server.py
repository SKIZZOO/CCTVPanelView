import os
import sys
import re
import time
import json
import socket
import threading
import secrets
import hmac
import math
from http.cookies import SimpleCookie
import urllib.parse
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any, List, Tuple

from core.ptz_controller import PTZController


def get_local_lan_ip() -> str:
    """Discovers the active local LAN IPv4 address (e.g. 192.168.1.50)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# Ultra-Modern CCTVPanelView 1:1 Surveillance Workstation Web App (Full Desktop Replica)
WORKSTATION_WEB_APP_HTML = """<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <link rel="icon" type="image/png" href="/assets/app_icon.png">
    <title>CCTVPanelView • Surveillance Workstation</title>
    <style>
        :root {
            --bg-base: #070b12;
            --bg-header: #0b0f19;
            --bg-sidebar: #0d1527;
            --bg-card: #131d2e;
            --bg-card-hover: #172338;
            --border: #1e293b;
            --border-subtle: #334155;
            --border-focus: #3b82f6;
            --text-main: #f8fafc;
            --text-sub: #cbd5e1;
            --text-muted: #94a3b8;
            --text-dark: #64748b;
            --accent-blue: #2563eb;
            --accent-blue-hover: #1d4ed8;
            --accent-cyan: #00e5ff;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-amber: #f59e0b;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            user-select: none;
            -webkit-user-select: none;
        }

        body {
            background-color: var(--bg-base);
            color: var(--text-main);
            font-family: var(--font-family);
            height: 100vh;
            width: 100vw;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        /* --- 1. Top Bar (Surveillance Workstation Navigation) --- */
        #topBar {
            height: 50px;
            min-height: 50px;
            background-color: var(--bg-header);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 14px;
            gap: 10px;
            z-index: 100;
        }

        .brand-container {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
        }

        .brand-logo-img {
            width: 26px;
            height: 26px;
            border-radius: 4px;
            object-fit: contain;
        }

        .brand-title {
            font-size: 14px;
            font-weight: 800;
            color: #f3f4f6;
            letter-spacing: 0.5px;
        }

        .brand-badge-live {
            font-size: 10px;
            font-weight: 700;
            color: #10b981;
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid #059669;
            padding: 1px 5px;
            border-radius: 3px;
            letter-spacing: 0.5px;
        }

        .top-btn {
            background-color: #0c1220;
            color: var(--text-sub);
            border: 1px solid var(--border);
            border-radius: 5px;
            padding: 5px 12px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
            white-space: nowrap;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .top-btn:hover {
            background-color: #162035;
            color: #ffffff;
            border-color: #38bdf8;
        }

        .top-btn.active {
            background-color: var(--accent-blue);
            color: #ffffff;
            border-color: #3b82f6;
        }

        /* Center Layout Buttons */
        .layout-btn-group {
            display: flex;
            align-items: center;
            gap: 4px;
            background: #090e18;
            padding: 3px;
            border-radius: 6px;
            border: 1px solid var(--border);
        }

        .layout-btn {
            background: transparent;
            color: var(--text-muted);
            border: none;
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .layout-btn:hover {
            color: #ffffff;
            background: rgba(255, 255, 255, 0.05);
        }

        .layout-btn.active {
            background-color: var(--accent-blue);
            color: #ffffff;
            border: 1px solid #3b82f6;
        }

        /* Top Action Buttons Group */
        .top-action-group {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        /* --- 2. Main Workspace Layout (Sidebar + Center Grid) --- */
        #workspace {
            flex: 1;
            height: calc(100vh - 50px);
            display: flex;
            overflow: hidden;
            position: relative;
        }

        /* --- Left Sidebar --- */
        #sidebar {
            width: 380px;
            min-width: 380px;
            max-width: 380px;
            background-color: var(--bg-sidebar);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), margin-left 0.25s ease;
            z-index: 50;
        }

        #sidebar.collapsed {
            margin-left: -380px;
        }

        /* Segmented Capsule Tabs */
        .side-tabs-header {
            display: flex;
            align-items: center;
            background: #090e1a;
            border-bottom: 1px solid var(--border);
            padding: 6px 8px;
            gap: 4px;
        }

        .side-tab-pill {
            flex: 1;
            background: transparent;
            color: var(--text-muted);
            border: none;
            border-radius: 4px;
            padding: 6px 8px;
            font-size: 11px;
            font-weight: 700;
            cursor: pointer;
            text-align: center;
            transition: all 0.15s ease;
            white-space: nowrap;
        }

        .side-tab-pill:hover {
            color: #ffffff;
            background: rgba(255, 255, 255, 0.04);
        }

        .side-tab-pill.active {
            background-color: #17243c;
            color: #38bdf8;
            border: 1px solid #1e3a5f;
        }

        .side-tab-btn-dock {
            background: transparent;
            color: var(--text-dark);
            border: none;
            font-size: 12px;
            padding: 4px 6px;
            cursor: pointer;
            border-radius: 4px;
        }
        .side-tab-btn-dock:hover { color: #ffffff; }

        .side-tab-content {
            flex: 1;
            display: none;
            flex-direction: column;
            overflow: hidden;
        }

        .side-tab-content.active {
            display: flex;
        }

        /* Alerts Tab Subheader */
        .alerts-subhdr {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 10px 4px 10px;
        }

        .incident-title {
            color: #94a3b8;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }

        .incident-badge {
            background-color: rgba(37, 99, 235, 0.15);
            color: #60a5fa;
            font-size: 10px;
            font-weight: 700;
            border: 1px solid #2563eb;
            border-radius: 4px;
            padding: 2px 7px;
        }

        .alerts-action-bar {
            display: flex;
            gap: 6px;
            padding: 4px 10px 8px 10px;
            border-bottom: 1px solid var(--border);
        }

        .alerts-action-btn {
            flex: 1;
            background-color: #0c1220;
            color: var(--text-sub);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 10px;
            font-weight: 600;
            cursor: pointer;
            text-align: center;
        }
        .alerts-action-btn:hover {
            background-color: #162035;
            color: #ffffff;
            border-color: #38bdf8;
        }

        /* Scrollable Feed Container */
        .alerts-feed-scroll {
            flex: 1;
            overflow-y: auto;
            padding: 8px 10px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .alerts-feed-scroll::-webkit-scrollbar {
            width: 6px;
        }
        .alerts-feed-scroll::-webkit-scrollbar-thumb {
            background: #1e293b;
            border-radius: 3px;
        }

        /* Rich Alert Card (1:1 with AlertCardWidget) */
        .alert-card {
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            border-left: 3px solid var(--accent-amber);
            border-radius: 5px;
            padding: 8px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            transition: all 0.15s ease;
        }

        .alert-card.alarm-person {
            border-left-color: var(--accent-red);
        }

        .alert-card:hover {
            border-color: #3b82f6;
            background-color: var(--bg-card-hover);
        }

        .alert-card-row1 {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 6px;
        }

        .alert-type-pill {
            font-size: 11px;
            font-weight: 700;
            border-radius: 4px;
            padding: 2px 6px;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .alert-type-pill.motion {
            background-color: rgba(245, 158, 11, 0.2);
            color: #f59e0b;
            border: 1px solid #f59e0b;
        }

        .alert-type-pill.person {
            background-color: rgba(239, 68, 68, 0.2);
            color: #ef4444;
            border: 1px solid #ef4444;
        }

        .alert-lens-badge {
            background-color: rgba(15, 23, 42, 0.9);
            color: #94a3b8;
            font-weight: 700;
            font-size: 10px;
            border: 1px solid #334155;
            border-radius: 4px;
            padding: 2px 6px;
        }

        .alert-time {
            color: #94a3b8;
            font-size: 11px;
            font-weight: 600;
            margin-left: auto;
        }

        .alert-dismiss-btn {
            background: transparent;
            color: #64748b;
            border: none;
            font-size: 12px;
            font-weight: bold;
            cursor: pointer;
            padding: 0 4px;
        }
        .alert-dismiss-btn:hover { color: #ef4444; }

        .alert-trigger-banner {
            color: #38bdf8;
            font-size: 10px;
            font-weight: 700;
            background-color: rgba(56, 189, 248, 0.12);
            border-left: 3px solid #38bdf8;
            padding: 3px 6px;
            border-radius: 2px;
            line-height: 1.3;
        }

        .alert-desc-text {
            color: #e2e8f0;
            font-size: 11px;
            font-weight: 600;
            line-height: 1.3;
        }

        .alert-media-row {
            display: flex;
            gap: 8px;
            align-items: center;
        }

        .alert-thumb-img {
            width: 80px;
            height: 45px;
            border-radius: 3px;
            object-fit: cover;
            border: 1px solid #334155;
            background: #000;
            cursor: pointer;
        }

        .alert-media-info {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .alert-cam-name {
            font-size: 11px;
            font-weight: 700;
            color: #ffffff;
        }

        .alert-clip-badge {
            font-size: 9px;
            font-weight: 700;
            color: #34d399;
        }

        .alert-card-actions {
            display: flex;
            gap: 6px;
            margin-top: 2px;
        }

        .alert-btn-play {
            flex: 1;
            background-color: #2563eb;
            color: #ffffff;
            border: 1px solid #3b82f6;
            border-radius: 4px;
            padding: 5px 8px;
            font-size: 11px;
            font-weight: 700;
            cursor: pointer;
            text-align: center;
        }
        .alert-btn-play:hover { background-color: #1d4ed8; }

        .alert-btn-snap {
            flex: 1;
            background-color: #0c1220;
            color: #cbd5e1;
            border: 1px solid #1a2336;
            border-radius: 4px;
            padding: 5px 8px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            text-align: center;
        }
        .alert-btn-snap:hover { background-color: #162035; color: #ffffff; border-color: #38bdf8; }

        /* Cameras Workspace Tab */
        .cam-tab-container {
            display: flex;
            flex-direction: column;
            gap: 6px;
            padding: 8px 10px;
            flex: 1;
            overflow-y: auto;
        }

        .cam-search-box {
            width: 100%;
            background: #080d17;
            border: 1px solid var(--border);
            border-radius: 4px;
            color: #ffffff;
            padding: 6px 10px;
            font-size: 11px;
            outline: none;
        }
        .cam-search-box:focus { border-color: var(--accent-blue); }

        .cam-actions-strip {
            display: flex;
            gap: 6px;
        }

        .cam-act-btn {
            flex: 1;
            background-color: #0c1220;
            color: #cbd5e1;
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 4px 6px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            text-align: center;
        }
        .cam-act-btn.primary {
            background-color: var(--accent-blue);
            color: #ffffff;
            border-color: #3b82f6;
        }

        .cam-tree-list {
            display: flex;
            flex-direction: column;
            gap: 6px;
            margin-top: 4px;
        }

        .cam-channel-card {
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 8px;
            display: flex;
            flex-direction: column;
            gap: 4px;
            cursor: pointer;
        }
        .cam-channel-card:hover {
            border-color: var(--accent-blue);
            background-color: var(--bg-card-hover);
        }

        .cam-channel-row1 {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .cam-ch-name {
            font-size: 12px;
            font-weight: 700;
            color: #f8fafc;
        }

        .cam-status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--accent-green);
            box-shadow: 0 0 6px var(--accent-green);
        }
        .cam-status-dot.offline {
            background-color: #64748b;
            box-shadow: none;
        }

        .cam-ch-meta {
            font-size: 10px;
            color: var(--text-muted);
            display: flex;
            gap: 8px;
        }

        .cam-ch-btns {
            display: flex;
            gap: 4px;
            margin-top: 4px;
        }

        .cam-mini-btn {
            background: #0a0f1c;
            color: #cbd5e1;
            border: 1px solid #1e293b;
            border-radius: 3px;
            padding: 2px 6px;
            font-size: 10px;
            cursor: pointer;
        }
        .cam-mini-btn:hover { background: #1e293b; color: #fff; }

        /* System HUD Tab */
        .hud-tab-container {
            padding: 10px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            overflow-y: auto;
            flex: 1;
        }

        .hud-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 8px;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .hud-card-title {
            font-size: 10px;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .hud-card-val {
            font-size: 16px;
            font-weight: 800;
            color: #38bdf8;
        }

        .hud-progress-bar {
            width: 100%;
            height: 4px;
            background: #1e293b;
            border-radius: 2px;
            overflow: hidden;
            margin-top: 2px;
        }

        .hud-progress-fill {
            height: 100%;
            background: #38bdf8;
            width: 0%;
        }

        /* Sidebar Footer Badges */
        .sidebar-footer {
            border-top: 1px solid var(--border);
            background: #090e1a;
            padding: 8px 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 4px;
        }

        .foot-badge {
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 3px;
            display: flex;
            align-items: center;
            gap: 4px;
            white-space: nowrap;
        }

        .foot-badge.green {
            color: #34d399;
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .foot-badge.purple {
            color: #c084fc;
            background: rgba(192, 132, 252, 0.12);
            border: 1px solid rgba(192, 132, 252, 0.3);
        }

        .foot-badge.cyan {
            color: #38bdf8;
            background: rgba(56, 189, 248, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.3);
        }

        /* --- 3. Center Video Grid Viewport --- */
        #viewport {
            flex: 1;
            padding: 6px;
            background-color: var(--bg-base);
            overflow: auto;
            position: relative;
        }

        #videoGrid {
            width: 100%;
            height: 100%;
            display: grid;
            gap: 6px;
        }

        /* Grid Layout Modes */
        #videoGrid.layout-1x1 {
            grid-template-columns: 1fr;
            grid-template-rows: 1fr;
        }

        #videoGrid.layout-2x2 {
            grid-template-columns: 1fr 1fr;
            grid-template-rows: 1fr 1fr;
        }

        #videoGrid.layout-3x3 {
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(3, 1fr);
        }

        #videoGrid.layout-dual {
            grid-template-columns: 1fr 1fr;
            grid-template-rows: 1fr;
        }

        /* Camera Video Tile (1:1 with VideoTile) */
        .video-tile {
            background-color: #000000;
            border: 1px solid var(--border);
            border-radius: 6px;
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            align-items: center;
        }

        .video-tile.selected {
            border-color: var(--accent-blue);
            box-shadow: 0 0 0 1px var(--accent-blue);
        }

        /* Live Stream Image */
        .tile-stream-img {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: contain;
            background-color: #000000;
        }

        .tile-connecting-text {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #64748b;
            font-size: 13px;
            font-weight: 600;
            pointer-events: none;
        }

        /* Centered Bottom Control Dock (1:1 with PC VideoTile.control_dock) */
        .tile-control-dock {
            position: absolute;
            bottom: 6px;
            left: 50%;
            transform: translateX(-50%) translateY(8px) scale(0.97);
            background-color: rgba(11, 15, 25, 0.94);
            border: 1px solid rgba(56, 189, 248, 0.30);
            border-radius: 6px;
            padding: 3px 6px;
            display: flex;
            align-items: center;
            gap: 4px;
            z-index: 20;
            white-space: nowrap;
            opacity: 0;
            pointer-events: none;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6);
            transition: opacity 0.24s cubic-bezier(0.16, 1, 0.3, 1),
                        transform 0.24s cubic-bezier(0.16, 1, 0.3, 1),
                        box-shadow 0.2s ease,
                        border-color 0.2s ease;
        }

        .video-tile:hover .tile-control-dock,
        .video-tile.alerting .tile-control-dock,
        .video-tile.recording .tile-control-dock {
            opacity: 1;
            pointer-events: auto;
            transform: translateX(-50%) translateY(0) scale(1);
            background-color: rgba(11, 15, 25, 0.98);
            border-color: rgba(56, 189, 248, 0.50);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.75), 0 0 15px rgba(56, 189, 248, 0.18);
        }

        .dock-pill {
            font-size: 11px;
            font-weight: 700;
            border-radius: 4px;
            padding: 2px 7px;
            display: flex;
            align-items: center;
        }

        .dock-pill.status-live {
            background-color: rgba(16, 185, 129, 0.20);
            color: #34d399;
            border: 1px solid #059669;
            animation: pulse-live-glow 2.5s infinite ease-in-out;
        }

        .dock-pill.status-connecting {
            background-color: rgba(245, 158, 11, 0.18);
            color: #fbbf24;
            border: 1px solid #d97706;
        }

        .dock-pill.name {
            background-color: rgba(15, 23, 42, 0.90);
            color: #f8fafc;
            border: 1px solid #334155;
            max-width: 140px;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .dock-badge-motion {
            background-color: rgba(225, 29, 72, 0.90);
            color: #ffffff;
            font-weight: 700;
            font-size: 10px;
            border-radius: 4px;
            padding: 2px 6px;
            border: 1px solid #fb7185;
            display: none;
            animation: pulse-motion-glow 1.2s infinite ease-in-out;
        }

        .dock-badge-signal {
            background-color: rgba(15, 23, 42, 0.90);
            color: #34d399;
            font-weight: 700;
            font-size: 11px;
            border-radius: 4px;
            padding: 2px 6px;
            border: 1px solid #334155;
        }

        .dock-btn {
            background-color: rgba(15, 23, 42, 0.90);
            color: #94a3b8;
            font-weight: 700;
            font-size: 10px;
            border: 1px solid #334155;
            border-radius: 4px;
            padding: 2px 6px;
            cursor: pointer;
            height: 22px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.18s cubic-bezier(0.16, 1, 0.3, 1),
                        background-color 0.18s ease,
                        border-color 0.18s ease,
                        color 0.18s ease,
                        box-shadow 0.18s ease;
        }

        .dock-btn:hover {
            background-color: #1e293b;
            color: #ffffff;
            border-color: #38bdf8;
            transform: translateY(-1.5px) scale(1.05);
            box-shadow: 0 4px 10px rgba(56, 189, 248, 0.25);
        }

        .dock-btn:active {
            transform: translateY(0.5px) scale(0.96);
            background-color: #0284c7;
        }

        .dock-btn.active {
            background-color: var(--accent-blue);
            color: #ffffff;
            border-color: #60a5fa;
            box-shadow: 0 0 10px rgba(59, 130, 246, 0.4);
        }

        .dock-btn.rec-active {
            background-color: #dc2626;
            color: #ffffff;
            border-color: #ef4444;
            animation: pulse-rec-glow 1.4s infinite ease-in-out;
        }

        @keyframes pulse-live-glow {
            0%, 100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); border-color: #059669; }
            50% { box-shadow: 0 0 8px 1px rgba(16, 185, 129, 0.45); border-color: #34d399; }
        }

        @keyframes pulse-rec-glow {
            0%, 100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); transform: scale(1); }
            50% { box-shadow: 0 0 10px 2px rgba(239, 68, 68, 0.55); transform: scale(1.03); }
        }

        @keyframes pulse-motion-glow {
            0%, 100% { box-shadow: 0 0 0 0 rgba(225, 29, 72, 0); opacity: 1; }
            50% { box-shadow: 0 0 10px 2px rgba(251, 113, 133, 0.6); opacity: 0.85; }
        }

        .dock-metrics {
            color: #94a3b8;
            font-size: 10px;
            font-weight: 700;
            background-color: rgba(15, 23, 42, 0.90);
            border-radius: 4px;
            padding: 2px 6px;
            border: 1px solid #334155;
        }

        /* --- 4. Modals (1:1 with PC Workstation Dialogs) --- */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-color: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            z-index: 500;
            display: none;
            align-items: center;
            justify-content: center;
        }

        .modal-overlay.open {
            display: flex;
        }

        .modal-window {
            background-color: #0b1120;
            border: 1px solid var(--border);
            border-radius: 8px;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.8);
            width: 860px;
            max-width: 95vw;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .modal-header {
            height: 48px;
            min-height: 48px;
            background: #070c18;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 16px;
        }

        .modal-title {
            font-size: 13px;
            font-weight: 800;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .modal-close-btn {
            background: transparent;
            color: var(--text-muted);
            border: none;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 4px;
        }
        .modal-close-btn:hover { color: #ffffff; background: rgba(255, 255, 255, 0.1); }

        .modal-body {
            flex: 1;
            padding: 16px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        /* PTZ Joystick Cluster */
        .ptz-grid {
            display: grid;
            grid-template-columns: repeat(3, 56px);
            grid-template-rows: repeat(3, 56px);
            gap: 6px;
            margin: 0 auto;
        }

        .ptz-key {
            background: #111c33;
            color: #38bdf8;
            border: 1px solid #1e3a5f;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 800;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
        }
        .ptz-key:active { background: #0284c7; color: #fff; }
        .ptz-key.stop { background: rgba(220, 38, 38, 0.2); color: #f87171; border-color: rgba(220, 38, 38, 0.4); }

        /* Floating Alert Toast Notification */
        #alertToast {
            position: fixed;
            top: 60px;
            right: 20px;
            background: rgba(15, 23, 42, 0.95);
            border: 1px solid #ef4444;
            border-left: 4px solid #ef4444;
            border-radius: 6px;
            padding: 10px 16px;
            display: flex;
            align-items: center;
            gap: 12px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.7);
            z-index: 1000;
            transform: translateX(450px);
            transition: transform 0.3s cubic-bezier(0.18, 0.89, 0.32, 1.28);
            cursor: pointer;
        }

        #alertToast.show {
            transform: translateX(0);
        }

        .toast-title { font-size: 11px; font-weight: 700; color: #f87171; }
        .toast-body { font-size: 12px; font-weight: 600; color: #ffffff; }
        #topBar { height: auto; min-height: 58px; padding: 10px 14px; flex-wrap: wrap; }
        #workspace { min-height: 0; height: auto; }
        .top-action-group { flex-wrap: wrap; }
        .top-btn:focus-visible, .layout-btn:focus-visible { outline: 2px solid var(--accent-cyan); outline-offset: 3px; }
        @media (max-width: 760px) {
            #topBar { gap: 8px; padding: 8px; }
            .brand-title { font-size: 12px; }
            .top-action-group { width: 100%; gap: 4px; }
            .top-btn { padding: 7px; }
        }
    </style>
</head>
<body>

    <!-- --- 1. Top Bar (1:1 with PC main_window.py top_bar) --- -->
    <header id="topBar">
        <!-- Left: Brand + Sidebar toggle -->
        <div class="brand-container" onclick="location.reload()">
            <img src="/assets/app_icon.png" alt="Logo" class="brand-logo-img">
            <span class="brand-title">CCTVPanelView</span>
            <span class="brand-badge-live">LIVE</span>
        </div>
        <button class="top-btn" id="btnToggleSidebar" onclick="toggleSidebar()">
            <span>Sidebar</span>
        </button>

        <!-- Center: Segmented Layout Controls -->
        <div class="layout-btn-group">
            <button class="layout-btn" data-layout="1x1" onclick="setLayout('1x1')">1x1</button>
            <button class="layout-btn active" data-layout="2x2" onclick="setLayout('2x2')">2x2</button>
            <button class="layout-btn" data-layout="3x3" onclick="setLayout('3x3')">3x3</button>
            <button class="layout-btn" data-layout="custom" onclick="openModal('customLayoutModal')">Custom</button>
            <button class="layout-btn" data-layout="dual" onclick="setLayout('dual')">Dual-Lens</button>
        </div>

        <!-- Right: Action Buttons Group -->
        <div class="top-action-group">
            <button class="top-btn" onclick="takeSnapshotAll()">Snapshot</button>
            <button class="top-btn" id="btnTopAlerts" onclick="openAlertsTab()">Alerts</button>
            <button class="top-btn" onclick="openModal('ptzModal')">PTZ Control</button>
            <button class="top-btn" onclick="openModal('intercomModal')">Intercom</button>
            <button class="top-btn" id="btnNightColor" onclick="toggleNightColor()">Night Color</button>
            <button class="top-btn" onclick="openModal('mobileModal')">Mobile Access</button>
            <button class="top-btn" onclick="openModal('recordingsModal')">Recordings</button>
            <button class="top-btn" onclick="openModal('settingsModal')">Settings</button>
            <button class="top-btn" onclick="toggleFullscreen()">[ ]</button>
        </div>
    </header>

    <!-- --- 2. Main Workspace Layout --- -->
    <div id="workspace">

        <!-- Left Dockable Sidebar -->
        <aside id="sidebar">
            <!-- 4 Capsule Segmented Tabs -->
            <div class="side-tabs-header">
                <button class="side-tab-pill" id="tabBtnCams" onclick="switchSideTab('cams')">Cameras (0)</button>
                <button class="side-tab-pill active" id="tabBtnAlerts" onclick="switchSideTab('alerts')">Alerts (0)</button>
                <button class="side-tab-pill" id="tabBtnHud" onclick="switchSideTab('hud')">System HUD</button>
                <button class="side-tab-btn-dock" onclick="toggleSidebar()" title="Collapse Sidebar">◀</button>
            </div>

            <!-- TAB 1: Live Alerts Feed (1:1 with desktop Alerts tab) -->
            <div class="side-tab-content active" id="tabContentAlerts">
                <div class="alerts-subhdr">
                    <span class="incident-title">INCIDENT FEED</span>
                    <span class="incident-badge" id="alertCountBadge">0 Events</span>
                </div>
                <div class="alerts-action-bar">
                    <button class="alerts-action-btn" onclick="clean30d()">Clean 30d</button>
                    <button class="alerts-action-btn" onclick="openModal('recordingsModal')">Video Clips</button>
                    <button class="alerts-action-btn" onclick="clearAllAlerts()">Clear All</button>
                </div>
                <div class="alerts-feed-scroll" id="alertsListContainer">
                    <!-- Dynamic AlertCards injected here -->
                </div>
            </div>

            <!-- TAB 0: Cameras Workspace -->
            <div class="side-tab-content" id="tabContentCams">
                <div class="cam-tab-container">
                    <input type="text" class="cam-search-box" id="camSearchInput" placeholder="Search cameras..." oninput="filterCameras()">
                    <div class="cam-actions-strip">
                        <button class="cam-act-btn primary" onclick="alert('Camera addition available via Workstation Settings.')">+ Add</button>
                        <button class="cam-act-btn" onclick="fetchCameras()">Scan LAN</button>
                        <button class="cam-act-btn" onclick="setLayout('2x2')">Stream All</button>
                    </div>
                    <div class="cam-tree-list" id="cameraTreeList">
                        <!-- Dynamic Camera Cards injected here -->
                    </div>
                </div>
            </div>

            <!-- TAB 2: System HUD -->
            <div class="side-tab-content" id="tabContentHud">
                <div class="hud-tab-container">
                    <div class="hud-card">
                        <span class="hud-card-title">CPU Telemetry</span>
                        <span class="hud-card-val" id="hudCpuVal">0%</span>
                        <div class="hud-progress-bar"><div class="hud-progress-fill" id="hudCpuBar"></div></div>
                    </div>
                    <div class="hud-card">
                        <span class="hud-card-title">Memory Allocation</span>
                        <span class="hud-card-val" id="hudMemVal">0%</span>
                        <div class="hud-progress-bar"><div class="hud-progress-fill" id="hudMemBar" style="background:#10b981;"></div></div>
                    </div>
                    <div class="hud-card">
                        <span class="hud-card-title">Primary Storage (NVMe/SSD)</span>
                        <span class="hud-card-val" id="hudDiskVal">0% Used</span>
                        <div class="hud-progress-bar"><div class="hud-progress-fill" id="hudDiskBar" style="background:#f59e0b;"></div></div>
                    </div>
                    <div class="hud-card">
                        <span class="hud-card-title">Active RTSP Feeds</span>
                        <span class="hud-card-val" id="hudStreamsVal">0 Live</span>
                    </div>
                    <div class="hud-card">
                        <span class="hud-card-title">LAN Web Clients</span>
                        <span class="hud-card-val" id="hudClientsVal">1 Connected</span>
                    </div>
                </div>
            </div>

            <!-- Sidebar Footer Badges -->
            <div class="sidebar-footer">
                <span class="foot-badge green">● Drive: Synced</span>
                <span class="foot-badge purple">● YOLOv8</span>
                <span class="foot-badge cyan" id="footPortBadge">● :8080 Live</span>
            </div>
        </aside>

        <!-- Center Camera Grid Viewport -->
        <main id="viewport">
            <div id="videoGrid" class="layout-2x2">
                <!-- Video Tiles dynamically populated here -->
            </div>
        </main>
    </div>

    <!-- --- 4. Modals --- -->

    <!-- In-Browser Video Player Modal (1:1 with PC VideoPlayerDialog) -->
    <div class="modal-overlay" id="videoPlayerModal">
        <div class="modal-window" style="width: 900px;">
            <div class="modal-header">
                <div class="modal-title">
                    <span id="playerModalCam">Camera Incident Clip</span>
                    <span class="incident-badge" id="playerModalBadge">AI ALERT</span>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <button class="top-btn" id="btnPlayerToggleView" onclick="togglePlayerView()">Clean Feed</button>
                    <button class="modal-close-btn" onclick="closePlayerModal()">✕</button>
                </div>
            </div>
            <div class="modal-body" style="padding:0; background:#000; align-items:center;">
                <video id="playerVideoEl" controls autoplay loop style="width:100%; max-height:65vh; background:#000; outline:none;"></video>
            </div>
            <div style="padding:10px 16px; background:#070c18; border-top:1px solid var(--border); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                <span style="font-size:11px; color:var(--text-muted);" id="playerVideoInfo">Recorded incident includes 0.5s trigger slate</span>
                <div style="display:flex; gap:6px; align-items:center;">
                    <button class="top-btn" onclick="stepPlayer(-1)" title="Step -1s (Left Arrow)">-1s</button>
                    <button class="top-btn" onclick="stepFrame(-1)" title="Step -1 Frame (Comma ',')">|&lt; Frame</button>
                    <button class="top-btn" onclick="stepFrame(1)" title="Step +1 Frame (Period '.')">Frame &gt;|</button>
                    <button class="top-btn" onclick="stepPlayer(1)" title="Step +1s (Right Arrow)">+1s</button>
                    <button class="top-btn" onclick="jumpTriggerWeb()" title="Jump to Trigger Action (0.5s) / Slate (0.0s)">Slate [0.5s]</button>
                    <button class="top-btn" onclick="snapCurrentWebFrame()" style="background:rgba(16,185,129,0.2); border-color:#10b981; color:#34d399;" title="Download HD Frame Snapshot">Snap Frame</button>
                    <a class="top-btn" id="playerDownloadBtn" href="" download style="text-decoration:none;">Download MP4</a>
                </div>
            </div>
        </div>
    </div>

    <!-- PTZ Controller Modal -->
    <div class="modal-overlay" id="ptzModal">
        <div class="modal-window" style="width: 440px;">
            <div class="modal-header">
                <span class="modal-title">PTZ Camera Control</span>
                <button class="modal-close-btn" onclick="closeModal('ptzModal')">✕</button>
            </div>
            <div class="modal-body" style="align-items:center;">
                <div style="width:100%; display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:11px; color:var(--text-muted);">Active Camera:</span>
                    <select id="ptzCamSelect" class="cam-search-box" style="width:200px;" onchange="updatePtzCam()"></select>
                </div>
                <div class="ptz-grid" style="margin-top:14px;">
                    <button class="ptz-key" onpointerdown="sendPTZ('up_left')" onpointerup="stopPTZ()">↖</button>
                    <button class="ptz-key" onpointerdown="sendPTZ('up')" onpointerup="stopPTZ()">▲</button>
                    <button class="ptz-key" onpointerdown="sendPTZ('up_right')" onpointerup="stopPTZ()">↗</button>
                    <button class="ptz-key" onpointerdown="sendPTZ('left')" onpointerup="stopPTZ()">◀</button>
                    <button class="ptz-key stop" onclick="stopPTZ()">■</button>
                    <button class="ptz-key" onpointerdown="sendPTZ('right')" onpointerup="stopPTZ()">▶</button>
                    <button class="ptz-key" onpointerdown="sendPTZ('down_left')" onpointerup="stopPTZ()">↙</button>
                    <button class="ptz-key" onpointerdown="sendPTZ('down')" onpointerup="stopPTZ()">▼</button>
                    <button class="ptz-key" onpointerdown="sendPTZ('down_right')" onpointerup="stopPTZ()">↘</button>
                </div>
                <div style="display:flex; gap:12px; width:100%; margin-top:10px;">
                    <button class="top-btn" style="flex:1; justify-content:center;" onpointerdown="sendPTZ('zoom_in')" onpointerup="stopPTZ()">Zoom +</button>
                    <button class="top-btn" style="flex:1; justify-content:center;" onpointerdown="sendPTZ('zoom_out')" onpointerup="stopPTZ()">Zoom -</button>
                </div>
                <div style="display:flex; gap:6px; width:100%; margin-top:8px;">
                    <button class="top-btn" style="flex:1; justify-content:center;" onclick="sendPTZ('preset_1')">P1 Curte</button>
                    <button class="top-btn" style="flex:1; justify-content:center;" onclick="sendPTZ('preset_2')">P2 Poarta</button>
                    <button class="top-btn" style="flex:1; justify-content:center;" onclick="sendPTZ('preset_3')">P3 Parcare</button>
                    <button class="top-btn" style="flex:1; justify-content:center;" onclick="sendPTZ('preset_4')">P4 Strada</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Mobile Access & QR Modal -->
    <div class="modal-overlay" id="mobileModal">
        <div class="modal-window" style="width: 480px;">
            <div class="modal-header">
                <span class="modal-title">Mobile Access & Remote Hub</span>
                <button class="modal-close-btn" onclick="closeModal('mobileModal')">✕</button>
            </div>
            <div class="modal-body" style="align-items:center; text-align:center;">
                <img src="/qr" alt="QR Link" style="width:200px; height:200px; border-radius:8px; border:1px solid var(--border); background:#fff; padding:6px;">
                <span style="font-size:12px; color:#38bdf8; font-weight:700; margin-top:8px;" id="qrLanUrl">http://192.168.1.50:8080</span>
                <p style="font-size:11px; color:var(--text-muted); line-height:1.4;">Scan with phone camera on same Wi-Fi or Tailscale network for immediate 1:1 mobile viewing with zero lag.</p>
            </div>
        </div>
    </div>

    <!-- Recordings Gallery Modal -->
    <div class="modal-overlay" id="recordingsModal">
        <div class="modal-window" style="width: 860px;">
            <div class="modal-header">
                <span class="modal-title">Recordings & Incident Archive</span>
                <button class="modal-close-btn" onclick="closeModal('recordingsModal')">✕</button>
            </div>
            <div class="modal-body">
                <div style="display:flex; gap:8px; margin-bottom:8px;">
                    <button class="top-btn active" onclick="loadRecordings('all')">All Clips</button>
                    <button class="top-btn" onclick="loadRecordings('ai')">AI Alarms</button>
                    <button class="top-btn" onclick="loadRecordings('motion')">Motion</button>
                </div>
                <div id="recordingsListContainer" style="display:flex; flex-direction:column; gap:6px;">
                    <!-- Dynamic list of recordings -->
                </div>
            </div>
        </div>
    </div>

    <!-- Settings Modal -->
    <div class="modal-overlay" id="settingsModal">
        <div class="modal-window" style="width: 500px;">
            <div class="modal-header">
                <span class="modal-title">Workstation Settings</span>
                <button class="modal-close-btn" onclick="closeModal('settingsModal')">✕</button>
            </div>
            <div class="modal-body">
                <div class="hud-card">
                    <span class="hud-card-title">Video Quality Preference</span>
                    <span style="font-size:11px; color:var(--text-sub);">Default stream resolution: 2K Ultra High Definition (2304x1296)</span>
                </div>
                <div class="hud-card">
                    <span class="hud-card-title">AI Detection Engine</span>
                    <span style="font-size:11px; color:var(--text-sub);">YOLOv8 Real-Time Person, Vehicle & Animal tracking with 0.5s baked incident slate.</span>
                </div>
                <div class="hud-card">
                    <span class="hud-card-title">Night Vision Boost</span>
                    <span style="font-size:11px; color:var(--text-sub);">Dynamic contrast adjustment and Full-Color White LED activation.</span>
                </div>
            </div>
        </div>
    </div>

    <!-- Intercom Modal -->
    <div class="modal-overlay" id="intercomModal">
        <div class="modal-window" style="width: 440px;">
            <div class="modal-header">
                <span class="modal-title">Two-Way Audio Intercom</span>
                <button class="modal-close-btn" onclick="closeModal('intercomModal')">✕</button>
            </div>
            <div class="modal-body" style="align-items:center; text-align:center;">
                <p style="font-size:12px; color:var(--text-sub);">Hold button to broadcast voice through camera speaker:</p>
                <button class="top-btn" style="margin:20px 0; width:160px; height:60px; font-size:14px; justify-content:center; background:#2563eb; color:#fff;" onpointerdown="startTalk()" onpointerup="stopTalk()">Hold to Talk</button>
                <span id="intercomStatus" style="font-size:11px; color:var(--text-muted);">Microphone Standby</span>
            </div>
        </div>
    </div>

    <!-- Floating Alert Toast Notification -->
    <div id="alertToast" onclick="onToastClicked()">
        <span class="toast-title">● INCIDENT ALERT</span>
        <span class="toast-body" id="toastMessage">Person detected at Entrance</span>
    </div>

    <!-- --- 5. Application JavaScript --- -->
    <script>
        let cameras = [];
        let alerts = [];
        let currentLayout = '2x2';
        let selectedCamId = null;
        let nightColorActive = false;
        let activePlayerAlert = null;
        let ptzCamIp = '';

        // Escape every dynamic HTML value, including attribute delimiters.
        // Nested markup must also use html``; event arguments use JSON strings.
        class SafeMarkup {
            constructor(markup) { this.markup = markup; }
            toString() { return this.markup; }
        }
        function html(parts, ...values) {
            const escape = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
            const markup = parts.reduce((out, part, i) => out + part + (i < values.length ? (values[i] instanceof SafeMarkup ? values[i].markup : escape(values[i])) : ''), '');
            return new SafeMarkup(markup);
        }
        function jsArg(value) { return JSON.stringify(String(value ?? '')); }
        function mediaUrl(value) {
            return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') && !value.includes(String.fromCharCode(92)) ? value : '';
        }

        // Layout definitions
        function setLayout(mode) {
            currentLayout = mode;
            document.querySelectorAll('.layout-btn').forEach(b => {
                b.classList.toggle('active', b.getAttribute('data-layout') === mode);
            });
            const grid = document.getElementById('videoGrid');
            grid.className = 'layout-' + mode;
            renderGrid();
        }

        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('collapsed');
        }

        function switchSideTab(tab) {
            document.querySelectorAll('.side-tab-pill').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.side-tab-content').forEach(c => c.classList.remove('active'));

            if (tab === 'cams') {
                document.getElementById('tabBtnCams').classList.add('active');
                document.getElementById('tabContentCams').classList.add('active');
            } else if (tab === 'alerts') {
                document.getElementById('tabBtnAlerts').classList.add('active');
                document.getElementById('tabContentAlerts').classList.add('active');
            } else if (tab === 'hud') {
                document.getElementById('tabBtnHud').classList.add('active');
                document.getElementById('tabContentHud').classList.add('active');
            }
        }

        function openAlertsTab() {
            document.getElementById('sidebar').classList.remove('collapsed');
            switchSideTab('alerts');
        }

        // Modal Handlers
        function openModal(id) {
            document.getElementById(id).classList.add('open');
            if (id === 'recordingsModal') loadRecordings('all');
        }
        function closeModal(id) {
            document.getElementById(id).classList.remove('open');
        }

        // Fullscreen
        function toggleFullscreen() {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen().catch(() => {});
            } else {
                document.exitFullscreen().catch(() => {});
            }
        }

        // Fetch Cameras
        async function fetchCameras() {
            try {
                const res = await fetch('/api/cameras');
                if (res.ok) {
                    cameras = await res.json();
                    document.getElementById('tabBtnCams').innerText = `Cameras (${cameras.length})`;
                    renderCameraTree();
                    renderGrid();
                    updatePtzCamSelect();
                }
            } catch (e) {
                console.error('Fetch cameras error:', e);
            }
        }

        function updatePtzCamSelect() {
            const sel = document.getElementById('ptzCamSelect');
            sel.innerHTML = '';
            cameras.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.camera_ip || c.id;
                opt.innerText = c.name || c.id;
                sel.appendChild(opt);
            });
            if (cameras.length > 0) ptzCamIp = sel.value;
        }

        function updatePtzCam() {
            ptzCamIp = document.getElementById('ptzCamSelect').value;
        }

        const hiddenStreams = new Set();
        // Render Center Video Grid
        function renderGrid() {
            const grid = document.getElementById('videoGrid');
            let visibleCameras = cameras.filter(c => !hiddenStreams.has(c.id));
            if (currentLayout === '1x1' && selectedCamId) {
                visibleCameras = visibleCameras.filter(c => c.id === selectedCamId);
            }
            let maxTiles = 4;
            if (currentLayout === '1x1') maxTiles = 1;
            else if (currentLayout === '2x2') maxTiles = 4;
            else if (currentLayout === '3x3') maxTiles = 9;
            else if (currentLayout === 'dual') maxTiles = 2;

            const signature = JSON.stringify([currentLayout, visibleCameras.slice(0, maxTiles).map(c => c.id)]);
            if (grid.dataset.signature === signature) {
                grid.querySelectorAll('.video-tile').forEach((tile, i) => {
                    const cam = visibleCameras[i];
                    tile.classList.toggle('selected', !!cam && cam.id === selectedCamId);
                    if (!cam) return;
                    const status = tile.querySelector('.dock-pill');
                    status.textContent = cam.is_online ? 'LIVE' : 'CONNECTING';
                    status.className = 'dock-pill ' + (cam.is_online ? 'status-live' : 'status-connecting');
                    const name = tile.querySelector('.dock-pill.name');
                    name.textContent = cam.name;
                    name.title = cam.name;
                    const rec = tile.querySelector('[data-record]');
                    rec.textContent = cam.is_recording ? '● ' + formatTime(cam.record_duration || 0) : '● REC';
                    rec.classList.toggle('rec-active', !!cam.is_recording);
                    tile.querySelector('.dock-metrics').textContent = `${cam.width || 1920}x${cam.height || 1080} • ${cam.fps || 15}fps`;
                });
                return;
            }
            grid.dataset.signature = signature;
            grid.replaceChildren();
            for (let i = 0; i < maxTiles; i++) {
                const cam = visibleCameras[i] || null;
                const tile = document.createElement('div');
                tile.className = 'video-tile' + (cam && cam.id === selectedCamId ? ' selected' : '');
                tile.onclick = () => { if (cam) selectCam(cam.id); };

                if (cam) {
                    const isRec = cam.is_recording;
                    const recDur = formatTime(cam.record_duration || 0);
                    const streamSrc = `/stream/${encodeURIComponent(cam.id)}?q=75&fps=15`;

                    tile.innerHTML = html`
                        <img class="tile-stream-img" id="stream_${cam.id}" src="${streamSrc}" alt="" onerror="onTileStreamErr(${jsArg(cam.id)})" />
                        
                        <!-- Centered Bottom Control Dock (1:1 with PC VideoTile) -->
                        <div class="tile-control-dock" onclick="event.stopPropagation()">
                            <span class="dock-pill ${cam.is_online ? 'status-live' : 'status-connecting'}">${cam.is_online ? 'LIVE' : 'CONNECTING'}</span>
                            <span class="dock-pill name" title="${cam.name}">${cam.name}</span>
                            <span class="dock-badge-motion" id="motion_${cam.id}">MOTION</span>

                            <button class="dock-btn" onclick="toggleColorTile(${jsArg(cam.id)})">Color</button>
                            <button class="dock-btn" onclick="toggleAudioTile(${jsArg(cam.id)})">Audio</button>
                            <button class="dock-btn" onclick="toggleQualityTile(${jsArg(cam.id)})">LOW</button>
                            <span class="dock-metrics">${cam.width || 1920}x${cam.height || 1080} • ${cam.fps || 15}fps</span>
                            <button class="dock-btn" onclick="takeSnapshotTile(${jsArg(cam.id)})">📸</button>
                            <button data-record class="dock-btn ${isRec ? 'rec-active' : ''}" onclick="toggleRecTile(${jsArg(cam.id)})">${isRec ? '● ' + recDur : '● REC'}</button>
                            <button class="dock-btn" onclick="soloTile(${jsArg(cam.id)})">[ ]</button>
                            <button class="dock-btn" onclick="closeTile(${jsArg(cam.id)})">X</button>
                        </div>
                    `;
                } else {
                    tile.innerHTML = html`
                        <span class="tile-connecting-text">No Camera Assigned</span>
                    `;
                }
                grid.appendChild(tile);
            }
        }

        function selectCam(id) {
            selectedCamId = id;
            hiddenStreams.delete(id);
            document.querySelectorAll('.video-tile').forEach(t => t.classList.remove('selected'));
            renderGrid();
        }

        function formatTime(s) {
            const m = Math.floor(s / 60);
            const sec = s % 60;
            return `${m < 10 ? '0' : ''}${m}:${sec < 10 ? '0' : ''}${sec}`;
        }

        // Render Cameras Workspace Tree
        function renderCameraTree() {
            const list = document.getElementById('cameraTreeList');
            list.innerHTML = '';
            cameras.forEach(c => {
                const card = document.createElement('div');
                card.className = 'cam-channel-card';
                card.onclick = () => selectCam(c.id);
                card.innerHTML = html`
                    <div class="cam-channel-row1">
                        <span class="cam-ch-name">${c.name}</span>
                        <span class="cam-status-dot ${c.is_online ? '' : 'offline'}"></span>
                    </div>
                    <div class="cam-ch-meta">
                        <span>${c.camera_ip || 'LAN'}</span>
                        <span>${c.width || 1920}x${c.height || 1080}</span>
                        <span>${c.fps || 15} FPS</span>
                    </div>
                    <div class="cam-ch-btns" onclick="event.stopPropagation()">
                        <button class="cam-mini-btn" onclick="soloTile(${jsArg(c.id)})">Solo</button>
                        <button class="cam-mini-btn" onclick="takeSnapshotTile(${jsArg(c.id)})">Snap</button>
                        <button class="cam-mini-btn" onclick="toggleRecTile(${jsArg(c.id)})">${c.is_recording ? 'Stop REC' : 'REC'}</button>
                    </div>
                `;
                list.appendChild(card);
            });
        }

        // Fetch Alerts
        async function fetchAlerts() {
            try {
                const res = await fetch('/api/alerts?limit=50');
                if (res.ok) {
                    const data = await res.json();
                    const newAlerts = data.alerts || [];
                    if (newAlerts.length > 0 && alerts.length > 0 && newAlerts[0].id !== alerts[0].id) {
                        showToastAlert(newAlerts[0]);
                    }
                    alerts = newAlerts;
                    document.getElementById('alertCountBadge').innerText = `${alerts.length} Events`;
                    document.getElementById('tabBtnAlerts').innerText = `Alerts (${alerts.length})`;
                    renderAlertsFeed();
                }
            } catch (e) {
                console.error('Fetch alerts error:', e);
            }
        }

        // Render Alerts Feed (1:1 with AlertCardWidget)
        function renderAlertsFeed() {
            const container = document.getElementById('alertsListContainer');
            container.innerHTML = '';
            alerts.forEach(a => {
                const isPerson = (a.label || '').toUpperCase().includes('PERSON');
                const tagColor = isPerson ? 'person' : 'motion';
                const card = document.createElement('div');
                card.className = `alert-card ${isPerson ? 'alarm-person' : ''}`;

                const snapUrl = mediaUrl(a.snapshot_url) || (a.unique_id ? `/api/alert_image/${encodeURIComponent(a.unique_id)}` : '/assets/app_icon.png');
                const vidUrl = mediaUrl(a.video_url) || (a.unique_id ? `/api/alert_video/${encodeURIComponent(a.unique_id)}` : '');

                card.innerHTML = html`
                    <div class="alert-card-row1">
                        <span class="alert-type-pill ${tagColor}">● ${a.label || 'ALERT'} (${Math.round((a.confidence || 0.85) * 100)}%)</span>
                        <span class="alert-lens-badge">${a.lens || 'L1'}</span>
                        <span class="alert-time">${a.time_short || (a.timestamp ? a.timestamp.split(' ')[1] : '')}</span>
                        <button class="alert-dismiss-btn" onclick="dismissAlert(${jsArg(a.id)})">✕</button>
                    </div>
                    ${a.trigger_reason ? html`<div class="alert-trigger-banner">Trigger: ${a.trigger_reason}</div>` : ''}
                    <div class="alert-desc-text">${a.description || a.camera_name + ' activity recorded'}</div>
                    <div class="alert-media-row">
                        <img class="alert-thumb-img" src="${snapUrl}" alt="Snap" onclick="openSnapshotUrl(${jsArg(snapUrl)})" />
                        <div class="alert-media-info">
                            <span class="alert-cam-name">${a.camera_name || 'Camera'}</span>
                            <span class="alert-clip-badge">Video Clip Available</span>
                        </div>
                    </div>
                    <div class="alert-card-actions">
                        <button class="alert-btn-play" onclick="openPlayerModal(${jsArg(a.id)})">Play Clip</button>
                        <button class="alert-btn-snap" onclick="openSnapshotUrl(${jsArg(snapUrl)})">Snapshot</button>
                    </div>
                `;
                container.appendChild(card);
            });
        }

        // Player Modal Actions
        function openPlayerModal(alertId) {
            const alertObj = alerts.find(a => a.id === alertId);
            if (!alertObj) return;
            activePlayerAlert = alertObj;

            const modal = document.getElementById('videoPlayerModal');
            document.getElementById('playerModalCam').innerText = `${alertObj.camera_name} • ${alertObj.lens || 'Main Stream'}`;
            document.getElementById('playerModalBadge').innerText = `${alertObj.label} (${Math.round((alertObj.confidence || 0.85) * 100)}%)`;

            const vidUrl = mediaUrl(alertObj.video_url) || `/api/alert_video/${encodeURIComponent(alertObj.unique_id)}`;
            const videoEl = document.getElementById('playerVideoEl');
            videoEl.src = vidUrl;
            videoEl.onplay = updatePlayerInfoFrame;
            videoEl.onpause = updatePlayerInfoFrame;
            videoEl.ontimeupdate = updatePlayerInfoFrame;
            videoEl.onwheel = (e) => {
                if (videoEl.paused) {
                    e.preventDefault();
                    stepFrame(e.deltaY < 0 ? 1 : -1);
                }
            };
            videoEl.play().catch(() => {});

            document.getElementById('playerDownloadBtn').href = vidUrl;
            document.getElementById('playerDownloadBtn').download = `${alertObj.camera_name}_${alertObj.unique_id}.mp4`;

            modal.classList.add('open');
        }

        function closePlayerModal() {
            const videoEl = document.getElementById('playerVideoEl');
            videoEl.pause();
            videoEl.src = '';
            document.getElementById('videoPlayerModal').classList.remove('open');
        }

        function stepPlayer(sec) {
            const videoEl = document.getElementById('playerVideoEl');
            videoEl.currentTime = Math.max(0, videoEl.currentTime + sec);
            updatePlayerInfoFrame();
        }

        function stepFrame(delta) {
            const videoEl = document.getElementById('playerVideoEl');
            videoEl.pause();
            const frameSec = 1.0 / 15.0;
            videoEl.currentTime = Math.max(0, videoEl.currentTime + (delta * frameSec));
            updatePlayerInfoFrame();
        }

        function jumpTriggerWeb() {
            const videoEl = document.getElementById('playerVideoEl');
            if (videoEl.currentTime < 0.6) {
                videoEl.currentTime = 0.5;
            } else {
                videoEl.currentTime = 0.0;
            }
            updatePlayerInfoFrame();
        }

        function snapCurrentWebFrame() {
            const videoEl = document.getElementById('playerVideoEl');
            if (!videoEl || !videoEl.videoWidth) return;
            const canvas = document.createElement('canvas');
            canvas.width = videoEl.videoWidth;
            canvas.height = videoEl.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
            canvas.toBlob(blob => {
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `snapshot_frame_${Math.round(videoEl.currentTime * 100) / 100}s.jpg`;
                a.click();
                URL.revokeObjectURL(url);
            }, 'image/jpeg', 0.95);
        }

        function updatePlayerInfoFrame() {
            const videoEl = document.getElementById('playerVideoEl');
            const infoEl = document.getElementById('playerVideoInfo');
            if (videoEl && infoEl) {
                const curFrame = Math.round(videoEl.currentTime * 15.0) + 1;
                const totFrames = videoEl.duration ? Math.round(videoEl.duration * 15.0) : '?';
                infoEl.innerText = `${videoEl.currentTime.toFixed(2)}s • Frame ${curFrame}/${totFrames} (15 fps)`;
            }
        }

        function openSnapshotUrl(url) {
            window.open(url, '_blank');
        }

        function showToastAlert(a) {
            const toast = document.getElementById('alertToast');
            document.getElementById('toastMessage').innerText = `${a.label} (${Math.round((a.confidence || 0.85)*100)}%) on ${a.camera_name}`;
            toast.classList.add('show');
            activePlayerAlert = a;
            setTimeout(() => toast.classList.remove('show'), 6000);
        }

        function onToastClicked() {
            if (activePlayerAlert) {
                openPlayerModal(activePlayerAlert.id);
            }
        }

        // Tile Actions
        async function toggleRecTile(streamId) {
            try {
                const res = await fetch(`/api/record?id=${encodeURIComponent(streamId)}&action=toggle`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}' });
                if (res.ok) {
                    fetchCameras();
                }
            } catch (e) {
                console.error(e);
            }
        }

        function takeSnapshotTile(streamId) {
            window.open(`/snapshot/${encodeURIComponent(streamId)}`, '_blank');
        }

        function soloTile(streamId) {
            selectedCamId = streamId;
            hiddenStreams.delete(streamId);
            setLayout('1x1');
        }

        function closeTile(streamId) {
            hiddenStreams.add(streamId);
            renderGrid();
        }

        function toggleNightColor() {
            nightColorActive = !nightColorActive;
            document.getElementById('btnNightColor').classList.toggle('active', nightColorActive);
            document.querySelectorAll('.tile-stream-img').forEach(img => {
                img.style.filter = nightColorActive ? 'contrast(1.4) saturate(1.2)' : 'none';
            });
        }

        function toggleColorTile(id) {
            const img = document.getElementById(`stream_${id}`);
            if (img) {
                const cur = img.style.filter;
                img.style.filter = (cur && cur !== 'none') ? 'none' : 'contrast(1.4) saturate(1.2)';
            }
        }

        function toggleAudioTile(id) {
            alert('Audio listening is available in the desktop application.');
        }

        function toggleQualityTile(id) {
            const img = document.getElementById(`stream_${id}`);
            if (!img) return;
            const low = img.dataset.lowQuality !== 'true';
            img.dataset.lowQuality = String(low);
            img.src = `/stream/${encodeURIComponent(id)}?q=${low ? 40 : 85}&fps=${low ? 8 : 15}`;
        }

        function onTileStreamErr(id) {
            setTimeout(() => {
                const img = document.getElementById(`stream_${id}`);
                if (img) img.src = `/stream/${encodeURIComponent(id)}?t=${Date.now()}`;
            }, 2000);
        }

        async function takeSnapshotAll() {
            window.open(`/snapshot/${encodeURIComponent(selectedCamId || (cameras[0] ? cameras[0].id : 'stream1'))}`, '_blank');
        }

        async function clearAllAlerts() {
            if (confirm('Clear all displayed incident alerts from history?')) {
                await fetch('/api/clear_alerts', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}' });
                fetchAlerts();
            }
        }

        function clean30d() {
            alert('Manage recording retention in the desktop application.');
        }

        // PTZ Commands
        async function sendPTZ(action) {
            if (!ptzCamIp && cameras.length > 0) ptzCamIp = cameras[0].camera_ip || cameras[0].id;
            try {
                await fetch(`/api/ptz?camera=${encodeURIComponent(ptzCamIp)}&action=${action}&speed=5`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}' });
            } catch (e) {
                console.error('PTZ send err:', e);
            }
        }

        async function stopPTZ() {
            sendPTZ('stop');
        }

        // Recordings list
        async function loadRecordings(filter) {
            const list = document.getElementById('recordingsListContainer');
            list.innerHTML = '<span style="font-size:11px; color:#94a3b8;">Loading archive...</span>';
            try {
                const res = await fetch('/api/recordings');
                if (res.ok) {
                    const data = await res.json();
                    const recs = data.recordings || [];
                    list.innerHTML = '';
                    if (recs.length === 0) {
                        list.innerHTML = '<span style="font-size:11px; color:#94a3b8;">No saved recordings found.</span>';
                        return;
                    }
                    recs.forEach(r => {
                        const item = document.createElement('div');
                        item.className = 'hud-card';
                        item.style.flexDirection = 'row';
                        item.style.justifyContent = 'space-between';
                        item.style.alignItems = 'center';
                        item.innerHTML = html`
                            <div>
                                <span style="font-size:11px; font-weight:700; color:#fff;">${r.name}</span>
                                <span style="font-size:10px; color:#94a3b8; display:block;">${r.date || ''} • ${r.size_mb || 0} MB</span>
                            </div>
                            <div style="display:flex; gap:6px;">
                                <a class="top-btn" href="${mediaUrl(r.url)}" target="_blank" style="text-decoration:none;">Play</a>
                                <a class="top-btn" href="${mediaUrl(r.url)}" download style="text-decoration:none;">Download</a>
                            </div>
                        `;
                        list.appendChild(item);
                    });
                }
            } catch (e) {
                list.innerHTML = '<span style="font-size:11px; color:#ef4444;">Failed to load recordings archive.</span>';
            }
        }

        // Telemetry update
        async function updateTelemetry() {
            try {
                const res = await fetch('/api/status');
                if (res.ok) {
                    const st = await res.json();
                    document.getElementById('hudCpuVal').innerText = `${st.cpu_percent || 0}%`;
                    document.getElementById('hudCpuBar').style.width = `${st.cpu_percent || 0}%`;
                    document.getElementById('hudMemVal').innerText = `${st.memory_percent || 0}%`;
                    document.getElementById('hudMemBar').style.width = `${st.memory_percent || 0}%`;
                    document.getElementById('hudDiskVal').innerText = `${st.disk_percent || 0}% Used`;
                    document.getElementById('hudDiskBar').style.width = `${st.disk_percent || 0}%`;
                    document.getElementById('hudStreamsVal').innerText = `${st.active_streams || 0} Live`;
                    document.getElementById('hudClientsVal').innerText = `${st.active_clients || 1} Connected`;
                    document.getElementById('qrLanUrl').innerText = `http://${st.lan_ip || '127.0.0.1'}:${st.port || 8080}`;
                    document.getElementById('footPortBadge').innerText = `● :${st.port || 8080} Live`;
                }
            } catch (e) {
                console.error(e);
            }
        }

        // Initialization
        window.addEventListener('DOMContentLoaded', async () => {
            const fragment = new URLSearchParams(location.hash.slice(1));
            let token = fragment.get('access');
            history.replaceState(null, '', location.pathname + location.search);
            if (!token && !(await fetch('/api/session')).ok) {
                token = prompt('Paste the access code after #access= from the desktop Mobile link.');
            }
            if (token) {
                const login = await fetch('/api/session', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({token})});
                if (!login.ok) { alert('Access denied. Reopen the link from the desktop Mobile dialog.'); return; }
            } else if (!(await fetch('/api/session')).ok) { return; }

            fetchCameras();
            fetchAlerts();
            updateTelemetry();
            setInterval(fetchCameras, 3000);
            setInterval(fetchAlerts, 3000);
            setInterval(updateTelemetry, 4000);
        });
    </script>
</body>
</html>"""

# Backward-compatible alias
MOBILE_WEB_APP_HTML = WORKSTATION_WEB_APP_HTML


class StreamingRequestHandler(BaseHTTPRequestHandler):
    """
    High-Performance HTTP Request Handler.
    Supports MJPEG live multipart video feeds, single-frame JPEG snapshots,
    JSON REST API endpoints (/api/cameras, /api/ptz), and full PWA Mobile Hub.
    """
    app_instance: Optional['WebStreamingServer'] = None

    @property
    def app(self) -> 'WebStreamingServer':
        inst = getattr(self.server, "app", None) or StreamingRequestHandler.app_instance
        return inst

    def log_message(self, format, *args):
        # Suppress routine 200/MJPEG log noise to keep console clean
        return

    def end_headers(self):
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        super().end_headers()

    def _authorized(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
            supplied = cookie["cctv_session"].value if "cctv_session" in cookie else ""
            if supplied and hmac.compare_digest(supplied, self.app.access_token):
                return True
        except (ValueError, TypeError):
            pass
        self.send_error(401, "Open the access link from the desktop Mobile dialog")
        return False

    def _read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 16384:
                self.send_error(413, "Request body too large")
                return None
            data = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(data, dict):
                raise ValueError("Expected an object")
            return data
        except (ValueError, UnicodeError):
            self.send_error(400, "Invalid JSON request")
            return None

    def _number(self, query, key, default, minimum, maximum, integer=False):
        try:
            value = float(query.get(key, [default])[0])
            if not math.isfinite(value):
                raise ValueError()
            return int(max(minimum, min(maximum, value))) if integer else max(minimum, min(maximum, value))
        except (ValueError, TypeError, OverflowError):
            return default

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. Main Mobile Web Hub
        if path == "/" or path == "/index.html":
            self._serve_mobile_app()
            return

        # 1b. Static Brand Logo & Favicon
        if path in ("/assets/app_icon.png", "/favicon.ico", "/logo.png", "/assets/cctvpanelview_logo.png"):
            self._serve_logo()
            return

        if not self._authorized():
            return
        if path == "/api/session":
            self._send_json({"success": True})
            return

        # 2. Live MJPEG Video Stream: /stream/<stream_id>
        if path.startswith("/stream/"):
            stream_id = urllib.parse.unquote(path[len("/stream/"):])
            self._serve_mjpeg_stream(stream_id, query)
            return

        # 3. Snapshot: /snapshot/<stream_id>
        if path.startswith("/snapshot/"):
            stream_id = urllib.parse.unquote(path[len("/snapshot/"):])
            self._serve_snapshot(stream_id, query)
            return

        # 4. JSON API: /api/cameras
        if path == "/api/cameras":
            self._serve_api_cameras()
            return

        # 5. JSON API: /api/status
        if path == "/api/status":
            self._serve_api_status()
            return

        # 5b. JSON API: /api/recordings
        if path == "/api/recordings":
            recs = self.app.get_recordings_list()
            self._send_json({"recordings": recs, "total": len(recs)})
            return

        # 5c. Serve Recording Video: /api/recording_file
        if path == "/api/recording_file":
            fn = query.get("file", [""])[0]
            self._serve_recording_file(fn)
            return

        # 5d. Clear Alerts: /api/clear_alerts
        if path == "/api/clear_alerts":
            self.send_error(405, "Use POST for changes")
            return

        # 6. JSON API: /api/alerts
        if path == "/api/alerts":
            limit = self._number(query, "limit", 50, 1, 200, integer=True)
            alerts = self.app.get_recent_alerts(limit=limit)
            self._send_json({"alerts": alerts, "total": len(alerts)})
            return

        # 7. Alert Snapshot Image: /api/alert_image/<unique_id>
        if path.startswith("/api/alert_image/"):
            uid = urllib.parse.unquote(path[len("/api/alert_image/"):])
            self._serve_alert_image(uid)
            return

        # 7b. Alert Video Stream: /api/alert_video/<unique_id>
        if path.startswith("/api/alert_video/"):
            uid = urllib.parse.unquote(path[len("/api/alert_video/"):])
            self._serve_alert_video(uid)
            return

        # 8. Recording Control & Status (GET): /api/record
        if path == "/api/record":
            stream_id = query.get("id", [""])[0] or query.get("stream", [""])[0]
            action = query.get("action", ["status"])[0]
            if action != "status":
                self.send_error(405, "Use POST for recording changes")
                return
            success, msg, details = self.app.handle_recording(stream_id, action)
            self._send_json({"success": success, "message": msg, **details})
            return

        # 9. QR Code direct image: /qr
        if path == "/qr":
            self._serve_qr_code()
            return

        # 10. Fallback: 404
        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        # JSON-only requests and same-origin cookies prevent cross-site form commands.
        origin = self.headers.get("Origin")
        if origin:
            parsed_origin = urllib.parse.urlsplit(origin)
            if parsed_origin.scheme not in ("http", "https") or parsed_origin.netloc != self.headers.get("Host"):
                self.send_error(403, "Cross-origin command rejected")
                return
        if self.headers.get_content_type() != "application/json":
            self.send_error(415, "Use application/json")
            return
        if path != "/api/session" and not self._authorized():
            return
        data = self._read_json_body()
        if data is None:
            return
        if path == "/api/session":
            token = data.get("token", "")
            if not isinstance(token, str) or not hmac.compare_digest(token.encode("utf-8"), self.app.access_token.encode("ascii")):
                self.send_error(401, "Invalid access code")
                return
            self.send_response(200)
            secure = "; Secure" if origin and urllib.parse.urlsplit(origin).scheme == "https" else ""
            self.send_header("Set-Cookie", f"cctv_session={self.app.access_token}; HttpOnly; SameSite=Strict; Path=/{secure}")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        query = urllib.parse.parse_qs(parsed.query)
        if path == "/api/clear_alerts":
            self._send_json({"success": self.app.clear_all_alerts()})
        elif path == "/api/ptz":
            camera_ip = query.get("camera", [""])[0]
            action = query.get("action", [""])[0]
            speed = self._number(query, "speed", 5, 1, 10, integer=True)
            success, msg = self.app.handle_ptz_command(camera_ip, action, speed)
            self._send_json({"success": success, "message": msg, "action": action})
        elif path == "/api/record":
            stream_id = query.get("id", [""])[0] or query.get("stream", [""])[0] or data.get("id", data.get("stream", ""))
            action = query.get("action", [data.get("action", "toggle")])[0]
            if not isinstance(stream_id, str) or not isinstance(action, str):
                self.send_error(400, "Invalid recording command")
                return
            success, msg, details = self.app.handle_recording(stream_id, action)
            self._send_json({"success": success, "message": msg, **details})
        elif path == "/api/delete_camera":
            # Desktop configuration changes must stay on the GUI thread.
            self.send_error(403, "Remove cameras from the desktop application")
        else:
            self.send_error(404, "Not Found")

    def _serve_mobile_app(self):
        body = MOBILE_WEB_APP_HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def _serve_mjpeg_stream(self, stream_id: str, query: Dict[str, List[str]]):
        worker = self.app.get_worker_for_stream(stream_id)
        if not worker:
            self.send_error(404, f"Camera stream '{stream_id}' not found or offline")
            return

        quality = self._number(query, "q", 65, 20, 95, integer=True)
        fps_limit = self._number(query, "fps", 15.0, 1.0, 30.0)
        frame_interval = 1.0 / max(1.0, min(30.0, fps_limit))
        is_raw = query.get("raw", ["0"])[0].lower() in ("1", "true", "yes") or query.get("view", [""])[0].lower() == "raw"

        self.app.increment_client_count(stream_id)
        try:
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()

            while self.app.is_running and worker.isRunning():
                t0 = time.time()
                jpeg_data = worker.get_latest_jpeg(quality=quality, raw=is_raw)
                if jpeg_data:
                    header = (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Content-Length: " + str(len(jpeg_data)).encode("ascii") + b"\r\n\r\n"
                    )
                    self.wfile.write(header + jpeg_data + b"\r\n")
                else:
                    time.sleep(0.015)

                elapsed = time.time() - t0
                sleep_time = max(0.005, frame_interval - elapsed)
                time.sleep(sleep_time)

        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception:
            pass
        finally:
            self.app.decrement_client_count(stream_id)

    def _serve_snapshot(self, stream_id: str, query: Optional[Dict[str, List[str]]] = None):
        worker = self.app.get_worker_for_stream(stream_id)
        if not worker:
            self.send_error(404, "Stream not found")
            return

        is_raw = False
        if query:
            is_raw = query.get("raw", ["0"])[0].lower() in ("1", "true", "yes") or query.get("view", [""])[0].lower() == "raw"

        jpeg = worker.get_latest_jpeg(quality=90, raw=is_raw)
        if not jpeg:
            self.send_error(503, "Camera frame not available yet")
            return

        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(jpeg)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Content-Disposition", 'inline; filename="snapshot.jpg"')
        self.end_headers()
        self.wfile.write(jpeg)

    def _serve_api_cameras(self):
        cams = self.app.get_camera_list()
        self._send_json(cams)

    def _serve_api_status(self):
        cpu_p = 0.0
        mem_p = 0.0
        disk_p = 0.0
        try:
            import psutil
            cpu_p = round(psutil.cpu_percent(interval=None), 1)
            mem_p = round(psutil.virtual_memory().percent, 1)
            disk_p = round(psutil.disk_usage('.').percent, 1)
        except Exception:
            pass

        workers = getattr(self.app.main_window, "active_workers", {})
        active_count = sum(1 for w in workers.values() if w and getattr(w, "status", "") == "LIVE")

        status = {
            "online": True,
            "lan_ip": self.app.lan_ip,
            "port": self.app.port,
            "active_clients": self.app.total_clients,
            "uptime_sec": int(time.time() - self.app.start_time),
            "cpu_percent": cpu_p,
            "memory_percent": mem_p,
            "disk_percent": disk_p,
            "active_streams": active_count,
            "total_streams": len(workers)
        }
        self._send_json(status)

    def _serve_video_file(self, target_path):
        try:
            with open(target_path, "rb") as video:
                size = os.fstat(video.fileno()).st_size
                start, end = 0, size - 1
                requested_range = self.headers.get("Range")
                if requested_range:
                    match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested_range.strip())
                    try:
                        if not match or not any(match.groups()):
                            raise ValueError()
                        first, last = match.groups()
                        if first:
                            start = int(first)
                            end = min(int(last), size - 1) if last else size - 1
                        else:
                            length = int(last)
                            if length <= 0:
                                raise ValueError()
                            start = max(0, size - length)
                        if start > end or start >= size:
                            raise ValueError()
                    except ValueError:
                        self.send_response(416)
                        self.send_header("Content-Range", f"bytes */{size}")
                        self.send_header("Content-Length", "0")
                        self.end_headers()
                        return
                self.send_response(206 if requested_range else 200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Length", str(max(0, end - start + 1)))
                self.send_header("Accept-Ranges", "bytes")
                if requested_range:
                    self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                filename = urllib.parse.quote(os.path.basename(target_path), safe="")
                self.send_header("Content-Disposition", f"inline; filename*=UTF-8''{filename}")
                self.send_header("Cache-Control", "private, no-store")
                self.end_headers()
                video.seek(start)
                remaining = max(0, end - start + 1)
                while remaining:
                    chunk = video.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionError, TimeoutError):
            pass
        except OSError:
            self.send_error(404, "Video unavailable")

    def _serve_recording_file(self, filename: str):
        # Reject drive-relative paths and NTFS streams as well as directory traversal.
        if (not filename or any(c in filename for c in ("..", "/", "\\", ":"))
                or not filename.lower().endswith(".mp4")):
            self.send_error(400, "Invalid recording filename")
            return
        for folder in ["recordings", os.path.join("recordings", "alarms")]:
            base = os.path.realpath(folder)
            candidate = os.path.realpath(os.path.join(base, filename))
            if os.path.commonpath([base, candidate]) == base and os.path.isfile(candidate):
                self._serve_video_file(candidate)
                return
        self.send_error(404, "Recording file not found")

    def _serve_alert_image(self, unique_id: str):
        mgr = getattr(self.app.main_window, "alert_manager", None)
        if not mgr:
            self.send_error(404, "AlertManager not active")
            return

        target_path = None
        with mgr.lock:
            for a in mgr.alerts_list:
                if a.get("unique_id") == unique_id and a.get("snapshot_path") and os.path.exists(a["snapshot_path"]):
                    target_path = a["snapshot_path"]
                    break

        if not target_path and hasattr(mgr, "snapshot_dir") and os.path.exists(mgr.snapshot_dir):
            for f in os.listdir(mgr.snapshot_dir):
                if unique_id in f and f.lower().endswith(".jpg"):
                    target_path = os.path.join(mgr.snapshot_dir, f)
                    break

        if not target_path or not os.path.exists(target_path):
            self.send_error(404, "Snapshot not found")
            return

        try:
            with open(target_path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "private, no-store")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(500, f"Error reading snapshot: {e}")

    def _serve_alert_video(self, unique_id: str):
        mgr = getattr(self.app.main_window, "alert_manager", None)
        if not mgr:
            self.send_error(404, "AlertManager not active")
            return

        target_path = None
        with mgr.lock:
            for a in mgr.alerts_list:
                if a.get("unique_id") == unique_id:
                    for key in ["video_highlighted_path", "video_path", "video_raw_path"]:
                        vp = a.get(key)
                        if vp and os.path.exists(vp) and os.path.getsize(vp) > 1024:
                            target_path = vp
                            break
                    if target_path:
                        break

        if not target_path and hasattr(mgr, "recording_dir") and os.path.exists(mgr.recording_dir):
            for f in os.listdir(mgr.recording_dir):
                if unique_id in f and f.lower().endswith(".mp4"):
                    p = os.path.join(mgr.recording_dir, f)
                    if os.path.getsize(p) > 1024:
                        target_path = p
                        break

        if not target_path or not os.path.exists(target_path):
            self.send_error(404, "Alert video not found or not finalized yet")
            return

        self._serve_video_file(target_path)

    def _serve_qr_code(self):
        url = self.app.get_local_url()
        png_data = self.app.generate_qr_png_bytes(url)
        if png_data:
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(png_data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "private, no-store")
            self.end_headers()
            self.wfile.write(png_data)
        else:
            self.send_error(500, "QR generation failed")

    def _serve_logo(self):
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "app_icon.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "private, no-store")
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404, "Logo asset not found")

    def _send_json(self, data: Any):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, *args, max_clients=32, **kwargs):
        self._slots = threading.BoundedSemaphore(max_clients)
        super().__init__(*args, **kwargs)

    def get_request(self):
        request, address = super().get_request()
        request.settimeout(10)
        return request, address

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            try:
                request.sendall(b"HTTP/1.0 503 Service Unavailable\r\nContent-Length: 0\r\n\r\n")
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


class WebStreamingServer:
    """
    Integrated Multi-Threaded Streaming Server for CAM720 Revamped.
    Allows local Wi-Fi and remote mobile viewing with zero CPU overhead when idle.
    """
    def __init__(self, main_window, port: int = 8080):
        self.main_window = main_window
        self.port = int(port)
        self.lan_ip = get_local_lan_ip()
        self.httpd: Optional[ReusableThreadingHTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.start_time = time.time()
        self.active_client_counts: Dict[str, int] = {}
        self.total_clients = 0
        self._lock = threading.Lock()
        self._ptz_controllers: Dict[str, PTZController] = {}
        self.access_token = secrets.token_urlsafe(32)

    def start(self) -> bool:
        """Starts the streaming server in a dedicated background daemon thread."""
        if self.is_running:
            return True

        try:
            StreamingRequestHandler.app_instance = self
            self.httpd = ReusableThreadingHTTPServer(("0.0.0.0", self.port), StreamingRequestHandler)
            self.httpd.app = self  # type: ignore
            self.port = self.httpd.server_address[1]
            self.access_token = secrets.token_urlsafe(32)
            self.is_running = True
            self.start_time = time.time()

            self.server_thread = threading.Thread(
                target=self.httpd.serve_forever,
                name="CCTVPanelView_WebStreamingServer",
                daemon=True
            )
            self.server_thread.start()
            print(f"[WebStreamingServer] Server running at: http://{self.lan_ip}:{self.port}")
            return True
        except Exception as e:
            print(f"[WebStreamingServer] Failed to bind port {self.port}: {e}")
            self.is_running = False
            return False

    def stop(self):
        """Stops the streaming server cleanly and releases resources."""
        if not self.is_running:
            return
        self.is_running = False
        with self._lock:
            for controller in list(self._ptz_controllers.values()):
                if hasattr(controller, "shutdown"):
                    try:
                        controller.shutdown()
                    except Exception:
                        pass
            self._ptz_controllers.clear()
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
        print("[WebStreamingServer] Server stopped cleanly.")

    def get_local_url(self) -> str:
        return f"http://{self.lan_ip}:{self.port}/#access={self.access_token}"

    def get_worker_for_stream(self, stream_id: str):
        """Retrieves active CameraStreamWorker from MainWindow."""
        if hasattr(self.main_window, "active_workers"):
            return self.main_window.active_workers.get(stream_id)
        return None

    def get_camera_list(self) -> List[Dict[str, Any]]:
        """Returns metadata for all configured cameras & streams."""
        res = []
        if hasattr(self.main_window, "device_manager"):
            for s in self.main_window.device_manager.get_all_streams():
                s_id = s.get("id")
                worker = self.get_worker_for_stream(s_id)
                cam_name = s.get("camera_name", "")
                s_name = s.get("name", s_id)
                display_name = f"{cam_name} • {s_name}" if cam_name and cam_name.lower() not in s_name.lower() else s_name
                is_online = bool(
                    worker and 
                    worker.isRunning() and 
                    worker.status == "LIVE" and 
                    getattr(worker, "_latest_bgr_frame", None) is not None
                )
                is_recording = bool(worker.is_recording) if (worker and hasattr(worker, "is_recording")) else False
                record_dur = int(worker.record_elapsed_seconds) if (worker and hasattr(worker, "record_elapsed_seconds")) else 0
                res.append({
                    "id": s_id,
                    "camera_id": s.get("camera_id", ""),
                    "camera_name": cam_name,
                    "name": display_name,
                    "stream_name": s_name,
                    "camera_ip": s.get("camera_ip", ""),
                    "is_ptz": bool(s.get("is_ptz", False)),
                    "is_online": is_online,
                    "status": worker.status if worker else "NONE",
                    "is_recording": is_recording,
                    "record_duration": record_dur,
                    "width": worker.width if worker else 1920,
                    "height": worker.height if worker else 1080,
                    "fps": worker.fps if worker else 15.0
                })
        return res

    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent detection incidents with what the camera saw, snapshot, and video links."""
        mgr = getattr(self.main_window, "alert_manager", None)
        if not mgr:
            return []
        with mgr.lock:
            result = []
            for a in mgr.alerts_list[:limit]:
                entry = dict(a)
                uid = entry.get("unique_id", "")
                if uid:
                    entry["snapshot_url"] = f"/api/alert_image/{uid}"
                    has_vid = False
                    for key in ["video_highlighted_path", "video_path", "video_raw_path"]:
                        vp = entry.get(key)
                        if vp and os.path.exists(vp) and os.path.getsize(vp) > 1024:
                            has_vid = True
                            break
                    if has_vid or entry.get("video_ready"):
                        entry["video_url"] = f"/api/alert_video/{uid}"
                        entry["has_video"] = True
                    else:
                        entry["has_video"] = False
                result.append(entry)
            return result

    def handle_recording(self, stream_id: str, action: str = "toggle") -> Tuple[bool, str, Dict[str, Any]]:
        """Starts, stops, or checks MP4 recording for a camera stream."""
        if not stream_id:
            return False, "Stream ID is missing", {}

        worker = self.get_worker_for_stream(stream_id)
        if not worker:
            return False, f"Camera '{stream_id}' is not active or could not be found", {}

        action = (action or "toggle").lower()
        if action == "toggle":
            action = "stop" if worker.is_recording else "start"

        if action == "start":
            if not worker.is_recording:
                worker.start_recording()
            return True, f"Recording started for {stream_id}", {
                "id": stream_id,
                "is_recording": True,
                "elapsed": worker.record_elapsed_seconds
            }
        elif action == "stop":
            if worker.is_recording:
                worker.stop_recording()
            return True, f"Recording stopped for {stream_id}", {
                "id": stream_id,
                "is_recording": False,
                "elapsed": 0
            }
        elif action == "status":
            return True, "Recording status", {
                "id": stream_id,
                "is_recording": worker.is_recording,
                "elapsed": worker.record_elapsed_seconds
            }
        return False, f"Unknown action: {action}", {}

    def increment_client_count(self, stream_id: str):
        with self._lock:
            self.active_client_counts[stream_id] = self.active_client_counts.get(stream_id, 0) + 1
            self.total_clients += 1
            worker = self.get_worker_for_stream(stream_id)
            if worker and hasattr(worker, "set_web_streaming_active"):
                worker.set_web_streaming_active(True)

    def decrement_client_count(self, stream_id: str):
        with self._lock:
            if stream_id in self.active_client_counts:
                self.active_client_counts[stream_id] = max(0, self.active_client_counts[stream_id] - 1)
                if self.active_client_counts[stream_id] == 0:
                    worker = self.get_worker_for_stream(stream_id)
                    if worker and hasattr(worker, "set_web_streaming_active"):
                        worker.set_web_streaming_active(False)
            self.total_clients = max(0, self.total_clients - 1)

    def handle_ptz_command(self, camera_ip: str, action: str, speed: int = 5) -> Tuple[bool, str]:
        """Dispatches PTZ movement to the hardware camera with strict SSRF protection & input validation."""
        clean_ip = str(camera_ip).strip()
        if not clean_ip or not re.match(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", clean_ip):
            return False, "Invalid or missing IP address"

        # SSRF Protection: strictly verify that clean_ip belongs to an authorized registered camera
        cam = None
        if hasattr(self.main_window, "device_manager"):
            cam = next((c for c in self.main_window.device_manager.get_cameras() if c.get("ip") == clean_ip), None)
        if not cam:
            return False, f"Access denied: IP '{clean_ip}' is not an authorized camera in the system"

        # Action validation: strictly allow only valid PTZ continuous directions or presets
        action_clean = str(action).lower().strip()
        is_preset = bool(re.match(r"^preset_[1-9][0-9]?$", action_clean))
        allowed_dirs = {"up", "down", "left", "right", "up_left", "up_right", "down_left", "down_right", "zoom_in", "zoom_out", "stop"}
        if action_clean not in allowed_dirs and not is_preset:
            return False, f"Invalid PTZ command: '{action_clean}'"

        speed_clamped = max(1, min(10, int(speed)))

        if clean_ip not in self._ptz_controllers:
            pwd = cam.get("password", "")
            user = cam.get("username", "admin")
            port = int(cam.get("onvif_port", 8899))
            try:
                self._ptz_controllers[clean_ip] = PTZController(clean_ip, username=user, password=pwd, port=port)
            except Exception as e:
                return False, str(e)

        controller = self._ptz_controllers[clean_ip]
        if action_clean == "stop":
            controller.stop()
            return True, "Stopped"
        elif is_preset:
            try:
                p_idx = int(action_clean.replace("preset_", ""))
                controller.goto_preset(p_idx)
                return True, f"Preset {p_idx}"
            except Exception as e:
                return False, str(e)
        else:
            controller.move(action_clean, speed_clamped)
            return True, f"Moving {action_clean}"

    def generate_qr_png_bytes(self, url: str) -> Optional[bytes]:
        """Generates raw PNG bytes of the QR Code."""
        try:
            import qrcode
            import io
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=8,
                border=2,
            )
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#000000", back_color="#ffffff")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception as e:
            print(f"[WebStreamingServer] QR Generation error: {e}")
            return None

    def get_recordings_list(self) -> List[Dict[str, Any]]:
        recs = []
        for folder in ["recordings", os.path.join("recordings", "alarms")]:
            if os.path.exists(folder):
                for f in os.listdir(folder):
                    if f.lower().endswith(".mp4") and not f.startswith("tmp_") and not f.startswith(".tmp"):
                        p = os.path.join(folder, f)
                        try:
                            stat = os.stat(p)
                            sz_mb = round(stat.st_size / (1024 * 1024), 1)
                            dt_str = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                            recs.append({
                                "name": f,
                                "size_mb": sz_mb,
                                "date": dt_str,
                                "mtime": stat.st_mtime,
                                "url": f"/api/recording_file?file={urllib.parse.quote(f)}"
                            })
                        except Exception:
                            pass
        recs.sort(key=lambda x: x["mtime"], reverse=True)
        return recs[:100]

    def clear_all_alerts(self) -> bool:
        mgr = getattr(self.main_window, "alert_manager", None)
        if mgr:
            with mgr.lock:
                mgr.alerts_list.clear()
                mgr._save_history()
            return True
        return False
