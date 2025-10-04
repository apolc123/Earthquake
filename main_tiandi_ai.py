# 运行命令: python main.py
# cmd运行 ssh -L 5000:localhost:5000 qinghe@10.140.34.26
# 然后浏览器打开:http://localhost:5000

from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit
import pandas as pd
import numpy as np
import logging
from werkzeug.utils import secure_filename
import os
import requests
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'earthquake-visualization-2024'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
socketio = SocketIO(app, cors_allowed_origins="*")

# 全局变量存储地震数据
earthquake_data = pd.DataFrame()

# AI API配置 - 请替换为你的API密钥
# 获取免费API密钥: https://open.bigmodel.cn/
AI_API_KEY = "9c1addac66334113a21add546ba7293b.ccJQfeoWQgbNtZaH"  # 请在这里填入你的智谱AI API密钥
AI_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

# HTML模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>广西地震灾害可视化地图</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 15px;
        }

        .container {
            max-width: 1800px;
            margin: 0 auto;
        }

         .header {
            background: white;
            padding: 25px 30px;
            border-radius: 15px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            margin-bottom: 20px;
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header-buttons {
            display: flex;
            gap: 10px;
        }

        .header-search-btn {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            color: white;
            border: none;
            padding: 12px 32px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            transition: all 0.3s;
            box-shadow: 0 2px 8px rgba(72, 187, 120, 0.3);
        }

        .header-search-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(72, 187, 120, 0.4);
        }

        .header-ai-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 32px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            transition: all 0.3s;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
        }

        .header-ai-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .header h1 {
            color: #2d3748;
            font-size: 2.2rem;
            margin-bottom: 8px;
            font-weight: 700;
        }

        .header p {
            color: #718096;
            font-size: 1rem;
        }

        .main-content {
            display: grid;
            grid-template-columns: 280px 1fr 350px;
            gap: 15px;
        }

        .center-column {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        }

        .card h3 {
            color: #2d3748;
            font-size: 1.1rem;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
        }

        .upload-area {
            border: 2px dashed #667eea;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            background: #f7fafc;
        }

        .upload-area:hover {
            background: #edf2f7;
            border-color: #5a67d8;
            transform: translateY(-2px);
        }

        .upload-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            width: 100%;
            font-weight: 600;
            transition: all 0.3s;
        }

        .upload-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .search-btn {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            width: 100%;
            font-weight: 600;
            transition: all 0.3s;
            margin-top: 10px;
        }

        .search-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(72, 187, 120, 0.4);
        }

        .filter-group {
            margin-bottom: 15px;
        }

        .filter-group label {
            display: block;
            color: #4a5568;
            font-size: 0.9rem;
            margin-bottom: 6px;
            font-weight: 500;
        }

        .filter-group input,
        .filter-group select {
            width: 100%;
            padding: 10px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 0.9rem;
            transition: border-color 0.3s;
        }

        .filter-group input:focus,
        .filter-group select:focus {
            outline: none;
            border-color: #667eea;
        }

        /* 信息检索弹窗 */
        .modal {
            display: none;
            position: fixed;
            z-index: 10000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.6);
            backdrop-filter: blur(5px);
            animation: fadeIn 0.3s;
        }

        .modal.show {
            display: flex;
            justify-content: center;
            align-items: center;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .modal-content {
            background: white;
            border-radius: 15px;
            width: 90%;
            max-width: 1200px;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            animation: slideIn 0.3s;
        }

        @keyframes slideIn {
            from { 
                transform: translateY(-50px);
                opacity: 0;
            }
            to { 
                transform: translateY(0);
                opacity: 1;
            }
        }

        .modal-header {
            padding: 20px 30px;
            border-bottom: 2px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 15px 15px 0 0;
        }

        .modal-header h2 {
            font-size: 1.5rem;
            font-weight: 600;
        }

        .close-btn {
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            font-size: 1.5rem;
            width: 35px;
            height: 35px;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .close-btn:hover {
            background: rgba(255,255,255,0.3);
            transform: rotate(90deg);
        }

        .modal-body {
            padding: 25px 30px;
            overflow-y: auto;
            flex: 1;
        }

        .search-form {
            background: #f7fafc;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }

        .search-form-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }

        .search-form-group {
            display: flex;
            flex-direction: column;
        }

        .search-form-group label {
            color: #4a5568;
            font-size: 0.9rem;
            margin-bottom: 6px;
            font-weight: 500;
        }

        .search-form-group input,
        .search-form-group select {
            padding: 10px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 0.9rem;
            transition: border-color 0.3s;
        }

        .search-form-group input:focus,
        .search-form-group select:focus {
            outline: none;
            border-color: #667eea;
        }

        .search-buttons {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
        }

        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.95rem;
            font-weight: 600;
            transition: all 0.2s;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .btn-secondary {
            background: #e2e8f0;
            color: #4a5568;
        }

        .btn-secondary:hover {
            background: #cbd5e1;
        }

        .search-results {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            overflow: hidden;
        }

        .results-header {
            background: #f7fafc;
            padding: 15px 20px;
            border-bottom: 2px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .results-header h3 {
            color: #2d3748;
            font-size: 1.1rem;
            font-weight: 600;
        }

        .results-count {
            color: #667eea;
            font-weight: 600;
            font-size: 1rem;
        }

        .results-table-wrapper {
            max-height: 400px;
            overflow-y: auto;
        }

        .results-table {
            width: 100%;
            border-collapse: collapse;
        }

        .results-table thead {
            position: sticky;
            top: 0;
            background: #f8fafc;
            z-index: 10;
        }

        .results-table th {
            padding: 12px 15px;
            text-align: left;
            font-weight: 600;
            color: #4a5568;
            border-bottom: 2px solid #e2e8f0;
            font-size: 0.9rem;
        }

        .results-table td {
            padding: 12px 15px;
            border-bottom: 1px solid #f1f5f9;
            color: #2d3748;
            font-size: 0.85rem;
        }

        .results-table tbody tr:hover {
            background: #f7fafc;
        }

        /* 地图容器优化 */
        .map-container {
            background: white;
            padding: 0;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            height: 500px;
            position: relative;
            overflow: hidden;
        }

        #mapPlot {
            width: 100%;
            height: calc(100% - 60px);
            margin-top: 60px;
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 1;
        }

        .map-header {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            background: linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.85) 100%);
            padding: 15px 20px;
            z-index: 1000;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #e2e8f0;
            backdrop-filter: blur(10px);
        }

        .map-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #2d3748;
        }

        .map-toggle-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            color: white;
            padding: 8px 18px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 600;
            transition: all 0.3s;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
        }

        .map-toggle-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        /* 时间轴控制面板 */
        .timeline-panel {
            background: white;
            padding: 18px 24px;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        }

        .timeline-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .timeline-title {
            font-size: 1rem;
            font-weight: 600;
            color: #2d3748;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .timeline-time-display {
            font-size: 1.1rem;
            font-weight: 700;
            color: #667eea;
            letter-spacing: 0.5px;
        }

        .timeline-slider-container {
            position: relative;
            margin-bottom: 15px;
        }

        .timeline-slider {
            width: 100%;
            height: 6px;
            border-radius: 3px;
            background: linear-gradient(90deg, #e2e8f0 0%, #cbd5e1 100%);
            outline: none;
            -webkit-appearance: none;
            cursor: pointer;
        }

        .timeline-slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
            transition: all 0.2s;
        }

        .timeline-slider::-webkit-slider-thumb:hover {
            transform: scale(1.2);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.6);
        }

        .timeline-slider::-moz-range-thumb {
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            cursor: pointer;
            border: none;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
            transition: all 0.2s;
        }

        .timeline-slider::-moz-range-thumb:hover {
            transform: scale(1.2);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.6);
        }

        .timeline-controls-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .timeline-buttons {
            display: flex;
            gap: 8px;
        }

        .timeline-btn {
            padding: 8px 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.85rem;
            font-weight: 600;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .timeline-btn.play {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            color: white;
            box-shadow: 0 2px 8px rgba(72, 187, 120, 0.3);
        }

        .timeline-btn.play:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(72, 187, 120, 0.4);
        }

        .timeline-btn.stop {
            background: linear-gradient(135deg, #f56565 0%, #e53e3e 100%);
            color: white;
            box-shadow: 0 2px 8px rgba(245, 101, 101, 0.3);
        }

        .timeline-btn.stop:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(245, 101, 101, 0.4);
        }

        .timeline-info-group {
            display: flex;
            align-items: center;
            gap: 20px;
        }

        .timeline-speed {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .timeline-speed label {
            font-size: 0.85rem;
            color: #4a5568;
            font-weight: 500;
        }

        .timeline-speed select {
            padding: 6px 12px;
            border: 2px solid #e2e8f0;
            border-radius: 6px;
            font-size: 0.85rem;
            cursor: pointer;
            background: white;
            font-weight: 500;
            transition: border-color 0.3s;
        }

        .timeline-speed select:focus {
            outline: none;
            border-color: #667eea;
        }

        .timeline-count {
            font-size: 0.85rem;
            color: #4a5568;
            font-weight: 500;
            background: #f7fafc;
            padding: 6px 12px;
            border-radius: 6px;
        }

        .timeline-count strong {
            color: #667eea;
            font-weight: 700;
        }

        /* 数据表格容器 */
        .data-table-container {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            height: 380px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        .table-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 12px;
            border-bottom: 2px solid #e2e8f0;
        }

        .table-header h3 {
            color: #2d3748;
            font-size: 1.1rem;
            margin: 0;
            font-weight: 600;
        }

        .table-info {
            color: #718096;
            font-size: 0.9rem;
        }

        .table-wrapper {
            flex: 1;
            overflow-y: auto;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }

        thead {
            position: sticky;
            top: 0;
            background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
            z-index: 10;
        }

        th {
            padding: 12px 10px;
            text-align: left;
            font-weight: 600;
            color: #4a5568;
            border-bottom: 2px solid #e2e8f0;
            white-space: nowrap;
        }

        td {
            padding: 10px;
            border-bottom: 1px solid #f1f5f9;
            color: #2d3748;
        }

        tbody tr:hover {
            background: #f7fafc;
        }

        .magnitude-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 0.8rem;
        }

        .magnitude-badge.weak {
            background: #c6f6d5;
            color: #22543d;
        }

        .magnitude-badge.felt {
            background: #fef3c7;
            color: #78350f;
        }

        .magnitude-badge.strong {
            background: #fed7d7;
            color: #742a2a;
        }

        .pagination {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
            margin-top: 15px;
            padding-top: 12px;
            border-top: 1px solid #e2e8f0;
        }

        .pagination button {
            padding: 6px 14px;
            border: 2px solid #e2e8f0;
            background: white;
            color: #4a5568;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
            font-weight: 500;
            transition: all 0.2s;
        }

        .pagination button:hover:not(:disabled) {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }

        .pagination button:disabled {
            opacity: 0.4;
            cursor: not-allowed;
        }

        .pagination .page-info {
            color: #718096;
            font-size: 0.85rem;
            font-weight: 500;
        }

        .view-btn {
            padding: 5px 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.8rem;
            font-weight: 600;
            transition: all 0.2s;
        }

        .view-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .right-panel {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .chart-card {
            background: white;
            padding: 15px;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        }

        #trendChart, #cityChart {
            width: 100%;
            height: 100%;
        }

        .success-msg {
            color: #22543d;
            background: #c6f6d5;
            padding: 12px;
            border-radius: 8px;
            margin-top: 10px;
            font-size: 0.9rem;
            font-weight: 500;
        }

        .error-msg {
            color: #742a2a;
            background: #fed7d7;
            padding: 12px;
            border-radius: 8px;
            margin-top: 10px;
            font-size: 0.9rem;
            font-weight: 500;
        }

        /* AI助手聊天窗口样式 */
        .ai-chat-container {
            display: none;
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 400px;
            height: 600px;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            z-index: 10001;
            flex-direction: column;
            overflow: hidden;
        }

        .ai-chat-container.show {
            display: flex;
            animation: slideUp 0.3s;
        }

        @keyframes slideUp {
            from {
                transform: translateY(100px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }

        .ai-chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .ai-chat-header h3 {
            font-size: 1.1rem;
            font-weight: 600;
        }

        .ai-chat-close {
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 1.2rem;
            transition: all 0.2s;
        }

        .ai-chat-close:hover {
            background: rgba(255,255,255,0.3);
            transform: rotate(90deg);
        }

        .ai-chat-messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: #f7fafc;
        }

        .ai-message {
            margin-bottom: 15px;
            display: flex;
            gap: 10px;
        }

        .ai-message.user {
            flex-direction: row-reverse;
        }

        .ai-message-avatar {
            width: 35px;
            height: 35px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            color: white;
            flex-shrink: 0;
            font-size: 0.85rem;
        }

        .ai-message.user .ai-message-avatar {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
        }

        .ai-message.assistant .ai-message-avatar {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }

        .ai-message-content {
            max-width: 70%;
            padding: 12px 15px;
            border-radius: 12px;
            line-height: 1.6;
            font-size: 0.9rem;
        }

        .ai-message.user .ai-message-content {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            color: white;
        }

        .ai-message.assistant .ai-message-content {
            background: white;
            color: #2d3748;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .ai-chat-input-container {
            padding: 15px 20px;
            background: white;
            border-top: 1px solid #e2e8f0;
        }

        .ai-chat-input-wrapper {
            display: flex;
            gap: 10px;
        }

        .ai-chat-input {
            flex: 1;
            padding: 10px 15px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 0.9rem;
            transition: border-color 0.3s;
        }

        .ai-chat-input:focus {
            outline: none;
            border-color: #667eea;
        }

        .ai-chat-send {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
        }

        .ai-chat-send:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .ai-chat-send:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .ai-typing {
            display: none;
            padding: 10px 15px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            width: fit-content;
        }

        .ai-typing.show {
            display: block;
        }

        .ai-typing-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #cbd5e1;
            margin: 0 2px;
            animation: typing 1.4s infinite;
        }

        .ai-typing-dot:nth-child(2) {
            animation-delay: 0.2s;
        }

        .ai-typing-dot:nth-child(3) {
            animation-delay: 0.4s;
        }

        @keyframes typing {
            0%, 60%, 100% {
                transform: translateY(0);
            }
            30% {
                transform: translateY(-10px);
            }
        }

        /* 地图悬浮信息框 */
        .map-tooltip {
            display: none;
            position: absolute;
            background: rgba(45, 55, 72, 0.95);
            color: white;
            padding: 16px;
            border-radius: 10px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
            z-index: 9999;
            min-width: 260px;
            font-size: 0.9rem;
            pointer-events: none;
            backdrop-filter: blur(10px);
        }

        .map-tooltip.show {
            display: block;
            animation: tooltipFadeIn 0.3s;
        }

        @keyframes tooltipFadeIn {
            from {
                opacity: 0;
                transform: translateY(-10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .tooltip-row {
            margin: 8px 0;
            line-height: 1.6;
        }

        .tooltip-label {
            font-weight: 600;
            margin-right: 6px;
        }

        /* 响应式优化 */
        @media (max-width: 1400px) {
            .main-content {
                grid-template-columns: 260px 1fr 320px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>广西地震灾害可视化地图</h1>
            </div>
            <div class="header-buttons">
                <button class="header-search-btn" onclick="openSearchModal()">信息检索</button>
                <button class="header-ai-btn" onclick="toggleAIChat()">🤖 AI助手</button>
            </div>
        </div>

        <div class="main-content">
            <!-- 左侧边栏 -->
            <div class="sidebar">
                <!-- 文件上传 -->
                <div class="card">
                    <h3>数据上传</h3>
                    <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                        <input type="file" id="fileInput" accept=".xlsx,.xls" style="display:none">
                        <button class="upload-btn">选择Excel文件</button>
                    </div>
                    <div id="uploadStatus"></div>
                </div>

                <!-- 统计信息面板 -->
                <div class="card">
                    <h3>统计信息</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div style="text-align: center; padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; color: white;">
                            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 5px;" id="totalRecords">0</div>
                            <div style="font-size: 0.85rem; opacity: 0.9;">记录总数</div>
                        </div>
                        <div style="text-align: center; padding: 15px; background: linear-gradient(135deg, #48bb78 0%, #38a169 100%); border-radius: 10px; color: white;">
                            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 5px;" id="avgMagnitude">0</div>
                            <div style="font-size: 0.85rem; opacity: 0.9;">平均震级</div>
                        </div>
                        <div style="text-align: center; padding: 15px; background: linear-gradient(135deg, #f56565 0%, #e53e3e 100%); border-radius: 10px; color: white;">
                            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 5px;" id="maxMagnitude">0</div>
                            <div style="font-size: 0.85rem; opacity: 0.9;">最大震级</div>
                        </div>
                        <div style="text-align: center; padding: 15px; background: linear-gradient(135deg, #ecc94b 0%, #d69e2e 100%); border-radius: 10px; color: white;">
                            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 5px;" id="avgDepth">0</div>
                            <div style="font-size: 0.85rem; opacity: 0.9;">平均深度(km)</div>
                        </div>
                    </div>
                </div>

                <!-- 地震类型分布 -->
                <div class="card" style="height: 420px;">
                    <div id="pieChart" style="width: 100%; height: 100%;"></div>
                </div>
            </div>

            <!-- 中间地图和数据表 -->
            <div class="center-column">
                <!-- 地图容器 -->
                <div class="map-container">
                    <div class="map-header">
                        <div class="map-title">广西壮族自治区地震分布图</div>
                        <button class="map-toggle-btn" onclick="toggleMapMode()">
                            <span id="mapModeText">切换为热力图</span>
                        </button>
                    </div>
                    <div id="mapPlot"></div>
                    <div id="mapTooltip" class="map-tooltip"></div>
                </div>

                <!-- 时间轴控制面板 -->
                <div class="timeline-panel" id="timelinePanel" style="display: none;">
                    <div class="timeline-header">
                        <div class="timeline-title">时间轴播放</div>
                        <div class="timeline-time-display" id="currentTimeDisplay">2020-01-01</div>
                    </div>

                    <div class="timeline-slider-container">
                        <input type="range" class="timeline-slider" id="timelineSlider" min="0" max="100" value="0">
                    </div>

                    <div class="timeline-controls-row">
                        <div class="timeline-buttons">
                            <button class="timeline-btn play" id="togglePlayBtn" onclick="togglePlayback()">播放</button>
                        </div>

                        <div class="timeline-info-group">
                            <div class="timeline-speed">
                                <label>速度:</label>
                                <select id="speedSelect" onchange="changeSpeed()">
                                    <option value="2000">慢</option>
                                    <option value="1000" selected>中</option>
                                    <option value="500">快</option>
                                    <option value="200">极快</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 数据列表 -->
                <div class="data-table-container">
                    <div class="table-header">
                        <h3>灾害事件简要信息列表</h3>
                        <span class="table-info">共 <strong id="tableTotal">0</strong> 条记录</span>
                    </div>
                    <div class="table-wrapper">
                        <table>
                            <thead>
                                <tr>
                                    <th style="width: 50px;">序号</th>
                                    <th style="width: 140px;">发生时间</th>
                                    <th style="width: 100px;">发生地区</th>
                                    <th style="width: 200px;">震中位置</th>
                                    <th style="width: 80px;">震级</th>
                                    <th style="width: 80px;">深度(km)</th>
                                    <th style="width: 100px;">灾害类型</th>
                                    <th style="width: 80px;">操作</th>
                                </tr>
                            </thead>
                            <tbody id="dataTableBody">
                                <tr>
                                    <td colspan="8" style="text-align: center; padding: 40px; color: #a0aec0;">
                                        暂无数据,请上传Excel文件
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="pagination">
                        <button onclick="changePage('first')" id="firstPageBtn">首页</button>
                        <button onclick="changePage('prev')" id="prevPageBtn">上一页</button>
                        <span class="page-info">
                            第 <strong id="currentPage">1</strong> 页 / 共 <strong id="totalPages">1</strong> 页
                        </span>
                        <button onclick="changePage('next')" id="nextPageBtn">下一页</button>
                        <button onclick="changePage('last')" id="lastPageBtn">末页</button>
                    </div>
                </div>
            </div>

            <!-- 右侧面板 -->
            <div class="right-panel">
                <!-- 年度趋势图 -->
                <div class="chart-card trend" style="height: 420px;">
                    <div id="trendChart"></div>
                </div>

                <!-- 城市分布图 -->
                <div class="chart-card city" style="height: 420px;">
                    <div id="cityChart"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- 信息检索弹窗 -->
    <div id="searchModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>地震信息检索</h2>
                <button class="close-btn" onclick="closeSearchModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="search-form">
                    <div class="search-form-row">
                        <div class="search-form-group" style="grid-column: span 2;">
                            <label>时间范围</label>
                            <div style="display: flex; gap: 10px; align-items: center;">
                                <input type="date" id="searchStartDate" style="flex: 1;">
                                <span style="color: #4a5568; font-weight: 600;">至</span>
                                <input type="date" id="searchEndDate" style="flex: 1;">
                            </div>
                        </div>
                        <div class="search-form-group">
                            <label>城市地区</label>
                            <select id="searchCity">
                                <option value="">全部城市</option>
                            </select>
                        </div>
                        <div class="search-form-group">
                            <label>最小震级</label>
                            <input type="number" id="searchMinMag" step="0.1" min="0" max="10" placeholder="如: 2.0">
                        </div>
                        <div class="search-form-group">
                            <label>最大震级</label>
                            <input type="number" id="searchMaxMag" step="0.1" min="0" max="10" placeholder="如: 5.0">
                        </div>
                    </div>
                    <div class="search-buttons">
                        <button class="btn btn-secondary" onclick="resetSearch()">重置</button>
                        <button class="btn btn-primary" onclick="executeSearch()">查询</button>
                    </div>
                </div>

                <div class="search-results">
                    <div class="results-header">
                        <h3>查询结果</h3>
                        <span class="results-count">共 <strong id="searchResultCount">0</strong> 条记录</span>
                    </div>
                    <div class="results-table-wrapper">
                        <table class="results-table">
                            <thead>
                                <tr>
                                    <th>序号</th>
                                    <th>发生时间</th>
                                    <th>城市</th>
                                    <th>震中位置</th>
                                    <th>震级</th>
                                    <th>深度(km)</th>
                                    <th>经度</th>
                                    <th>纬度</th>
                                    <th>类型</th>
                                </tr>
                            </thead>
                            <tbody id="searchResultsBody">
                                <tr>
                                    <td colspan="9" style="text-align: center; padding: 40px; color: #a0aec0;">
                                        暂无数据
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="pagination" style="margin-top: 15px;">
                        <button onclick="changeSearchPage('first')" id="searchFirstPageBtn">首页</button>
                        <button onclick="changeSearchPage('prev')" id="searchPrevPageBtn">上一页</button>
                        <span class="page-info">
                            第 <strong id="searchCurrentPage">1</strong> 页 / 共 <strong id="searchTotalPages">1</strong> 页
                        </span>
                        <button onclick="changeSearchPage('next')" id="searchNextPageBtn">下一页</button>
                        <button onclick="changeSearchPage('last')" id="searchLastPageBtn">末页</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- AI助手聊天窗口 -->
    <div class="ai-chat-container" id="aiChatContainer">
        <div class="ai-chat-header">
            <h3>🤖 地震知识AI助手</h3>
            <button class="ai-chat-close" onclick="toggleAIChat()">&times;</button>
        </div>
        <div class="ai-chat-messages" id="aiChatMessages">
            <div class="ai-message assistant">
                <div class="ai-message-avatar">AI</div>
                <div class="ai-message-content">
                    你好!我是地震知识AI助手。你可以问我关于地震、地震灾害、防震减灾等相关问题,我会尽力为你解答。
                </div>
            </div>
        </div>
        <div class="ai-chat-input-container">
            <div class="ai-chat-input-wrapper">
                <input type="text" class="ai-chat-input" id="aiChatInput" placeholder="输入你的问题..." onkeypress="handleAIChatKeyPress(event)">
                <button class="ai-chat-send" id="aiChatSend" onclick="sendAIMessage()">发送</button>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let currentMapMode = 'scatter';
        let currentData = [];
        let currentPage = 1;
        let pageSize = 10;
        let totalPages = 1;

        let timelineData = [];
        let timelineInterval = null;
        let currentTimelineIndex = 0;
        let isPlaying = false;
        let playSpeed = 1000;
        let sortedTimelineData = [];

        let searchResults = [];
        let searchCurrentPage = 1;
        let searchPageSize = 20;
        let searchTotalPages = 1;


        let leafletMap = null;
        let currentMarkers = [];
        let heatmapLayer = null;
        const TIANDITU_KEY = '9078a195b8c193988ee91e3945aa118c';

        socket.on('connect', function() {
            console.log('已连接到服务器');
        });

        socket.on('disconnect', function() {
            console.log('连接断开');
        });

        // ==================== AI助手功能 ====================
        function toggleAIChat() {
            const container = document.getElementById('aiChatContainer');
            container.classList.toggle('show');
        }

        function handleAIChatKeyPress(event) {
            if (event.key === 'Enter') {
                sendAIMessage();
            }
        }

        function sendAIMessage() {
            const input = document.getElementById('aiChatInput');
            const message = input.value.trim();

            if (!message) return;

            addMessage('user', message);
            input.value = '';

            const sendBtn = document.getElementById('aiChatSend');
            sendBtn.disabled = true;
            sendBtn.textContent = '发送中...';

            showTypingIndicator();

            fetch('/api/ai/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: message })
            })
            .then(response => response.json())
            .then(data => {
                hideTypingIndicator();
                if (data.success) {
                    addMessage('assistant', data.response);
                } else {
                    addMessage('assistant', '抱歉,我遇到了一些问题: ' + data.error);
                }
            })
            .catch(error => {
                hideTypingIndicator();
                console.error('AI请求错误:', error);
                addMessage('assistant', '抱歉,网络连接出现问题,请稍后再试。');
            })
            .finally(() => {
                sendBtn.disabled = false;
                sendBtn.textContent = '发送';
            });
        }

        function addMessage(role, content) {
            const messagesContainer = document.getElementById('aiChatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `ai-message ${role}`;

            const avatar = document.createElement('div');
            avatar.className = 'ai-message-avatar';
            avatar.textContent = role === 'user' ? '你' : 'AI';

            const contentDiv = document.createElement('div');
            contentDiv.className = 'ai-message-content';
            contentDiv.textContent = content;

            messageDiv.appendChild(avatar);
            messageDiv.appendChild(contentDiv);
            messagesContainer.appendChild(messageDiv);

            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        function showTypingIndicator() {
            const messagesContainer = document.getElementById('aiChatMessages');
            const typingDiv = document.createElement('div');
            typingDiv.className = 'ai-message assistant';
            typingDiv.id = 'typingIndicator';

            const avatar = document.createElement('div');
            avatar.className = 'ai-message-avatar';
            avatar.textContent = 'AI';

            const typingContent = document.createElement('div');
            typingContent.className = 'ai-typing show';
            typingContent.innerHTML = '<span class="ai-typing-dot"></span><span class="ai-typing-dot"></span><span class="ai-typing-dot"></span>';

            typingDiv.appendChild(avatar);
            typingDiv.appendChild(typingContent);
            messagesContainer.appendChild(typingDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        function hideTypingIndicator() {
            const indicator = document.getElementById('typingIndicator');
            if (indicator) {
                indicator.remove();
            }
        }

        // ==================== 检索弹窗功能 ====================
        function openSearchModal() {
            if (currentData.length === 0) {
                alert('请先上传数据文件');
                return;
            }

            const cities = [...new Set(currentData.map(d => d.city))].sort();
            const citySelect = document.getElementById('searchCity');
            citySelect.innerHTML = '<option value="">全部城市</option>';
            cities.forEach(city => {
                const option = document.createElement('option');
                option.value = city;
                option.textContent = city;
                citySelect.appendChild(option);
            });

            searchResults = [...currentData];
            searchCurrentPage = 1;
            displaySearchResults(searchResults);

            document.getElementById('searchModal').classList.add('show');
        }

        function closeSearchModal() {
            document.getElementById('searchModal').classList.remove('show');
        }

        function resetSearch() {
            document.getElementById('searchStartDate').value = '';
            document.getElementById('searchEndDate').value = '';
            document.getElementById('searchCity').value = '';
            document.getElementById('searchMinMag').value = '';
            document.getElementById('searchMaxMag').value = '';

            document.getElementById('searchResultsBody').innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; padding: 40px; color: #a0aec0;">
                        请设置查询条件后点击"查询"按钮
                    </td>
                </tr>
            `;
            document.getElementById('searchResultCount').textContent = '0';
        }

        function executeSearch() {
            let results = [...currentData];

            const startDate = document.getElementById('searchStartDate').value;
            const endDate = document.getElementById('searchEndDate').value;
            if (startDate) {
                results = results.filter(d => d.time >= startDate);
            }
            if (endDate) {
                results = results.filter(d => d.time <= endDate + ' 23:59:59');
            }

            const city = document.getElementById('searchCity').value;
            if (city) {
                results = results.filter(d => d.city === city);
            }

            const minMag = parseFloat(document.getElementById('searchMinMag').value);
            const maxMag = parseFloat(document.getElementById('searchMaxMag').value);
            if (!isNaN(minMag)) {
                results = results.filter(d => d.magnitude >= minMag);
            }
            if (!isNaN(maxMag)) {
                results = results.filter(d => d.magnitude <= maxMag);
            }

            searchCurrentPage = 1;
            displaySearchResults(results);
        }

        function displaySearchResults(results) {
            searchResults = results;
            searchTotalPages = Math.ceil(results.length / searchPageSize);
            document.getElementById('searchResultCount').textContent = results.length;
            document.getElementById('searchTotalPages').textContent = searchTotalPages;

            renderSearchPage();
        }

        function renderSearchPage() {
            const tbody = document.getElementById('searchResultsBody');
            const start = (searchCurrentPage - 1) * searchPageSize;
            const end = start + searchPageSize;
            const pageData = searchResults.slice(start, end);

            if (pageData.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="9" style="text-align: center; padding: 40px; color: #a0aec0;">
                            未找到符合条件的数据
                        </td>
                    </tr>
                `;
                updateSearchPagination();
                return;
            }

            let html = '';
            pageData.forEach((item, index) => {
                const globalIndex = start + index + 1;
                const type = classifyEarthquake(item.magnitude);
                let badgeClass = 'weak';
                if (type === '有感地震') badgeClass = 'felt';
                if (type === '中强震') badgeClass = 'strong';

                html += `
                    <tr>
                        <td>${globalIndex}</td>
                        <td>${item.time.substring(0, 19)}</td>
                        <td>${item.city}</td>
                        <td>${item.location}</td>
                        <td><span class="magnitude-badge ${badgeClass}">${item.magnitude}级</span></td>
                        <td>${item.depth}</td>
                        <td>${item.longitude.toFixed(4)}</td>
                        <td>${item.latitude.toFixed(4)}</td>
                        <td>${type}</td>
                    </tr>
                `;
            });

            tbody.innerHTML = html;
            document.getElementById('searchCurrentPage').textContent = searchCurrentPage;
            updateSearchPagination();
        }

        function updateSearchPagination() {
            document.getElementById('searchFirstPageBtn').disabled = searchCurrentPage === 1;
            document.getElementById('searchPrevPageBtn').disabled = searchCurrentPage === 1;
            document.getElementById('searchNextPageBtn').disabled = searchCurrentPage === searchTotalPages || searchTotalPages === 0;
            document.getElementById('searchLastPageBtn').disabled = searchCurrentPage === searchTotalPages || searchTotalPages === 0;
        }

        function changeSearchPage(action) {
            switch(action) {
                case 'first':
                    searchCurrentPage = 1;
                    break;
                case 'prev':
                    if (searchCurrentPage > 1) searchCurrentPage--;
                    break;
                case 'next':
                    if (searchCurrentPage < searchTotalPages) searchCurrentPage++;
                    break;
                case 'last':
                    searchCurrentPage = searchTotalPages;
                    break;
            }
            renderSearchPage();
        }

        window.onclick = function(event) {
            const modal = document.getElementById('searchModal');
            if (event.target === modal) {
                closeSearchModal();
            }
        }

        // ==================== 文件上传 ====================
        document.getElementById('fileInput').addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;

            if (!file.name.match(/\.(xlsx|xls)$/i)) {
                document.getElementById('uploadStatus').innerHTML = 
                    '<div class="error-msg">请选择Excel文件 (.xlsx 或 .xls)</div>';
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            document.getElementById('uploadStatus').innerHTML = 
                '<div style="color: #667eea; padding: 10px; font-weight: 500;">正在上传文件...</div>';

            fetch('/api/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('上传失败');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    document.getElementById('uploadStatus').innerHTML = 
                        `<div class="success-msg">已加载 ${data.count} 条地震记录</div>`;

                    loadMap();
                } else {
                    document.getElementById('uploadStatus').innerHTML = 
                        `<div class="error-msg">${data.error}</div>`;
                }
            })
            .catch(error => {
                console.error('上传错误:', error);
                document.getElementById('uploadStatus').innerHTML = 
                    `<div class="error-msg">上传失败: ${error.message}</div>`;
            });
        });

        // ==================== 地图初始化 ====================
        function initLeafletMap() {
            if (leafletMap) {
                leafletMap.remove();
            }

            leafletMap = L.map('mapPlot', {
                center: [23.5, 108],
                zoom: 7,
                zoomControl: true
            });

            L.tileLayer('http://t{s}.tianditu.gov.cn/vec_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=vec&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=' + TIANDITU_KEY, {
                subdomains: ['0', '1', '2', '3', '4', '5', '6', '7'],
                attribution: '&copy; 天地图'
            }).addTo(leafletMap);

            L.tileLayer('http://t{s}.tianditu.gov.cn/cva_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=cva&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=' + TIANDITU_KEY, {
                subdomains: ['0', '1', '2', '3', '4', '5', '6', '7']
            }).addTo(leafletMap);

            setTimeout(() => {
                if (leafletMap) {
                    leafletMap.invalidateSize();
                    console.log('地图尺寸已刷新');
                }
            }, 100);
        }

        function loadMap() {
            fetch('/api/data')
            .then(response => response.json())
            .then(data => {
                if (data.length === 0) {
                    return;
                }

                currentData = data;
                updateStatistics(data);
                plotMap(data);
                plotPieChart(data);
                plotTrendChart(data);
                plotCityChart(data);
                updateDataTable(data);
                initializeTimeline(data);
            })
            .catch(error => {
                console.error('加载数据错误:', error);
            });
        }

        function updateStatistics(data) {
            if (data.length === 0) {
                document.getElementById('totalRecords').textContent = '0';
                document.getElementById('avgMagnitude').textContent = '0';
                document.getElementById('maxMagnitude').textContent = '0';
                document.getElementById('avgDepth').textContent = '0';
                return;
            }

            document.getElementById('totalRecords').textContent = data.length;

            const avgMag = data.reduce((sum, d) => sum + d.magnitude, 0) / data.length;
            document.getElementById('avgMagnitude').textContent = avgMag.toFixed(1);

            const maxMag = Math.max(...data.map(d => d.magnitude));
            document.getElementById('maxMagnitude').textContent = maxMag.toFixed(1);

            const avgDep = data.reduce((sum, d) => sum + d.depth, 0) / data.length;
            document.getElementById('avgDepth').textContent = avgDep.toFixed(1);
        }

        // ==================== 时间轴功能 ====================
        function initializeTimeline(data) {
            if (data.length === 0) {
                document.getElementById('timelinePanel').style.display = 'none';
                return;
            }

            sortedTimelineData = [...data].sort((a, b) => {
                return new Date(a.time) - new Date(b.time);
            });

            const groupedByDate = {};
            sortedTimelineData.forEach(d => {
                const date = d.time.substring(0, 10);
                if (!groupedByDate[date]) {
                    groupedByDate[date] = [];
                }
                groupedByDate[date].push(d);
            });

            const dateKeys = Object.keys(groupedByDate).sort();
            sortedTimelineData = dateKeys.map(date => ({
                date: date,
                earthquakes: groupedByDate[date]
            }));

            document.getElementById('timelinePanel').style.display = 'block';

            const startTime = sortedTimelineData[0].date;
            document.getElementById('currentTimeDisplay').textContent = startTime;

            const slider = document.getElementById('timelineSlider');
            slider.max = sortedTimelineData.length - 1;
            slider.value = 0;

            currentTimelineIndex = 0;

            slider.addEventListener('input', function() {
                if (isPlaying) {
                    stopPlayback();
                }
                currentTimelineIndex = parseInt(this.value);
                updateTimelineDisplay();
            });
        }

        function togglePlayback() {
            if (isPlaying) {
                stopPlayback();
            } else {
                startPlayback();
            }
        }

        function startPlayback() {
            if (sortedTimelineData.length === 0) return;

            isPlaying = true;
            const btn = document.getElementById('togglePlayBtn');
            btn.innerHTML = '暂停';
            btn.className = 'timeline-btn stop';

            timelineInterval = setInterval(() => {
                if (currentTimelineIndex < sortedTimelineData.length - 1) {
                    currentTimelineIndex++;
                    updateTimelineDisplay();
                } else {
                    stopPlayback();
                }
            }, playSpeed);
        }

        function stopPlayback() {
            isPlaying = false;
            clearInterval(timelineInterval);

            const btn = document.getElementById('togglePlayBtn');
            btn.innerHTML = '播放';
            btn.className = 'timeline-btn play';

            currentTimelineIndex = 0;
            document.getElementById('timelineSlider').value = 0;

            if (currentData.length > 0) {
                plotScatterMap(currentData);
                const startTime = sortedTimelineData[0].date;
                document.getElementById('currentTimeDisplay').textContent = startTime;
            }
        }

        function changeSpeed() {
            playSpeed = parseInt(document.getElementById('speedSelect').value);
            if (isPlaying) {
                clearInterval(timelineInterval);
                timelineInterval = setInterval(() => {
                    if (currentTimelineIndex < sortedTimelineData.length - 1) {
                        currentTimelineIndex++;
                        updateTimelineDisplay();
                    } else {
                        stopPlayback();
                    }
                }, playSpeed);
            }
        }

        function updateTimelineDisplay() {
            document.getElementById('timelineSlider').value = currentTimelineIndex;

            const dayData = sortedTimelineData[currentTimelineIndex];
            const displayData = dayData.earthquakes;

            document.getElementById('currentTimeDisplay').textContent = dayData.date;

            plotTimelineMap(displayData);
        }

        function plotTimelineMap(data) {
            if (!leafletMap) {
                initLeafletMap();
            }

            currentMarkers.forEach(marker => leafletMap.removeLayer(marker));
            currentMarkers = [];
            if (heatmapLayer) {
                leafletMap.removeLayer(heatmapLayer);
                heatmapLayer = null;
            }

            data.forEach(d => {
                const size = Math.max(d.magnitude * 4 + 3, 6);
                const marker = L.circleMarker([d.latitude, d.longitude], {
                    radius: size / 2,
                    fillColor: '#48bb78',
                    color: '#fff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.8
                }).addTo(leafletMap);

                const type = classifyEarthquake(d.magnitude);
                marker.bindPopup(`
                    <div style="font-family: 'Microsoft YaHei', sans-serif;">
                        <strong style="font-size: 14px;">${d.location}</strong><br>
                        <div style="margin-top: 8px; line-height: 1.6;">
                            <b>时间:</b> ${d.time}<br>
                            <b>城市:</b> ${d.city}<br>
                            <b>震级:</b> ${d.magnitude}级<br>
                            <b>深度:</b> ${d.depth}km<br>
                            <b>类型:</b> ${type}
                        </div>
                    </div>
                `);

                currentMarkers.push(marker);
            });
        }

        function classifyEarthquake(magnitude) {
            if (magnitude >= 1.0 && magnitude < 3.0) return '弱震';
            if (magnitude >= 3.0 && magnitude < 4.5) return '有感地震';
            if (magnitude >= 4.5) return '中强震';
            return '其他';
        }

        function toggleMapMode() {
            if (isPlaying) {
                stopPlayback();
            }

            if (currentMapMode === 'scatter') {
                currentMapMode = 'heatmap';
                document.getElementById('mapModeText').innerHTML = '切换为散点图';
                document.getElementById('timelinePanel').style.display = 'none';
            } else {
                currentMapMode = 'scatter';
                document.getElementById('mapModeText').innerHTML = '切换为热力图';
                if (currentData.length > 0) {
                    document.getElementById('timelinePanel').style.display = 'block';
                }
            }

            if (currentData.length > 0) {
                plotMap(currentData);
            }
        }

        function plotMap(data) {
            if (currentMapMode === 'scatter') {
                plotScatterMap(data);
            } else {
                plotHeatMap(data);
            }
        }

        function plotScatterMap(data) {
            if (!leafletMap) {
                initLeafletMap();
            }

            currentMarkers.forEach(marker => leafletMap.removeLayer(marker));
            currentMarkers = [];
            if (heatmapLayer) {
                leafletMap.removeLayer(heatmapLayer);
                heatmapLayer = null;
            }

            const groups = {
                '弱震': { data: [], color: '#48bb78' },
                '有感地震': { data: [], color: '#ecc94b' },
                '中强震': { data: [], color: '#f56565' }
            };

            data.forEach(d => {
                const type = classifyEarthquake(d.magnitude);
                if (groups[type]) {
                    groups[type].data.push(d);
                }
            });

            Object.keys(groups).forEach(groupName => {
                const group = groups[groupName];
                group.data.forEach(d => {
                    const size = Math.max(d.magnitude * 4 + 3, 6);
                    const marker = L.circleMarker([d.latitude, d.longitude], {
                        radius: size / 2,
                        fillColor: group.color,
                        color: '#fff',
                        weight: 1,
                        opacity: 0.8,
                        fillOpacity: 0.6
                    }).addTo(leafletMap);

                    marker.bindPopup(`
                        <div style="font-family: 'Microsoft YaHei', sans-serif;">
                            <strong style="font-size: 14px;">${d.location}</strong><br>
                            <div style="margin-top: 8px; line-height: 1.6;">
                                <b>时间:</b> ${d.time}<br>
                                <b>城市:</b> ${d.city}<br>
                                <b>震级:</b> ${d.magnitude}级<br>
                                <b>深度:</b> ${d.depth}km<br>
                                <b>类型:</b> ${groupName}
                            </div>
                        </div>
                    `);

                    currentMarkers.push(marker);
                });
            });

            if (currentMarkers.length > 0) {
                const group = L.featureGroup(currentMarkers);
                leafletMap.flyToBounds(group.getBounds(), {
                    padding: [50, 50],
                    maxZoom: 9,
                    duration: 1.5
                });
            }

            setTimeout(() => {
                if (leafletMap) {
                    leafletMap.invalidateSize();
                }
            }, 50);
        }

        function plotHeatMap(data) {
            if (!leafletMap) {
                initLeafletMap();
            }

            currentMarkers.forEach(marker => leafletMap.removeLayer(marker));
            currentMarkers = [];
            if (heatmapLayer) {
                leafletMap.removeLayer(heatmapLayer);
            }

            const heatData = data.map(d => [
                d.latitude, 
                d.longitude, 
                d.magnitude / 10
            ]);

            heatmapLayer = L.heatLayer(heatData, {
                radius: 25,
                blur: 15,
                maxZoom: 10,
                max: 1.0,
                gradient: {
                    0.0: 'rgba(255, 255, 255, 0)',
                    0.2: 'rgba(234, 179, 8, 0.3)',
                    0.5: 'rgba(249, 115, 22, 0.6)',
                    0.8: 'rgba(239, 68, 68, 0.8)',
                    1.0: 'rgba(220, 38, 38, 0.95)'
                }
            }).addTo(leafletMap);
        }

        // ==================== 图表绘制 ====================
        function plotPieChart(data) {
            const classification = {
                '弱震': 0,
                '有感地震': 0,
                '中强震': 0
            };

            data.forEach(d => {
                const type = classifyEarthquake(d.magnitude);
                if (classification[type] !== undefined) {
                    classification[type]++;
                }
            });

            const pieData = [{
                values: [classification['弱震'], classification['有感地震'], classification['中强震']],
                labels: ['弱震', '有感地震', '中强震'],
                type: 'pie',
                marker: {
                    colors: ['#48bb78', '#ecc94b', '#f56565']
                },
                textinfo: 'label+percent',
                textposition: 'inside',
                textfont: {
                    size: 14,
                    color: 'white'
                },
                hovertemplate: '<b>%{label}</b><br>数量: %{value} 次<br>占比: %{percent}<extra></extra>'
            }];

            const pieLayout = {
                title: {
                    text: '地震类型分布统计',
                    font: { size: 16, color: '#2d3748' }
                },
                showlegend: true,
                legend: {
                    orientation: 'v',
                    y: -0.2,
                    x: 0.5,
                    xanchor: 'center',
                    yanchor: 'top',
                    font: { size: 13 }
                },
                margin: { t: 50, b: 80, l: 10, r: 10 },
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                autosize: true
            };

            const config = {
                responsive: true,
                displayModeBar: false
            };

            Plotly.newPlot('pieChart', pieData, pieLayout, config);
        }

        function plotTrendChart(data) {
            const yearCount = {};
            data.forEach(d => {
                const year = d.time.substring(0, 4);
                yearCount[year] = (yearCount[year] || 0) + 1;
            });

            const years = Object.keys(yearCount).sort();
            const counts = years.map(year => yearCount[year]);

            const trendData = [{
                x: years,
                y: counts,
                type: 'scatter',
                mode: 'lines+markers+text',
                line: {
                    color: '#667eea',
                    width: 3
                },
                marker: {
                    color: '#667eea',
                    size: 10,
                    line: {
                        color: 'white',
                        width: 2
                    }
                },
                text: counts,
                textposition: 'top center',
                textfont: {
                    size: 14,
                    color: '#2d3748',
                    family: 'Microsoft YaHei, Arial'
                },
                hovertemplate: '<b>%{x}年</b><br>地震次数: %{y}次<extra></extra>'
            }];

            const trendLayout = {
                title: {
                    text: '年度地震频次趋势(2020-2025)',
                    font: { size: 14, color: '#2d3748' }
                },
                xaxis: {
                    title: {
                        text: '年份',
                        font: { size: 12, color: '#4a5568' }
                    },
                    tickfont: { size: 11, color: '#718096' }
                },
                yaxis: {
                    title: {
                        text: '地震次数',
                        font: { size: 12, color: '#4a5568' }
                    },
                    tickfont: { size: 11, color: '#718096' },
                    rangemode: 'tozero'
                },
                margin: { t: 40, b: 40, l: 50, r: 15 },
                paper_bgcolor: 'rgba(255,255,255,0)',
                plot_bgcolor: 'rgba(248,250,252,1)',
                showlegend: false,
                autosize: true
            };

            const config = {
                responsive: true,
                displayModeBar: false
            };

            Plotly.newPlot('trendChart', trendData, trendLayout, config);
        }

        function plotCityChart(data) {
            const cityCount = {};
            data.forEach(d => {
                cityCount[d.city] = (cityCount[d.city] || 0) + 1;
            });

            const sortedCities = Object.entries(cityCount)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 15);

            const cities = sortedCities.map(item => item[0]);
            const counts = sortedCities.map(item => item[1]);

            const cityData = [{
                x: cities,
                y: counts,
                type: 'bar',
                marker: {
                    color: '#764ba2',
                    line: {
                        color: 'white',
                        width: 1
                    }
                },
                text: counts,
                textposition: 'outside',
                textfont: {
                    size: 12,
                    color: '#2d3748',
                    family: 'Microsoft YaHei, Arial'
                },
                hovertemplate: '<b>%{x}</b><br>地震次数: %{y}次<extra></extra>'
            }];

            const cityLayout = {
                title: {
                    text: '地震市区分布(2020-2025)',
                    font: { size: 14, color: '#2d3748' }
                },
                xaxis: {
                    title: {
                        text: '地区',
                        font: { size: 12, color: '#4a5568' }
                    },
                    tickfont: { size: 10, color: '#718096' },
                    tickangle: -45
                },
                yaxis: {
                    title: {
                        text: '地震次数',
                        font: { size: 12, color: '#4a5568' }
                    },
                    tickfont: { size: 11, color: '#718096' },
                    rangemode: 'tozero'
                },
                margin: { t: 40, b: 70, l: 50, r: 15 },
                paper_bgcolor: 'rgba(255,255,255,0)',
                plot_bgcolor: 'rgba(248,250,252,1)',
                showlegend: false,
                autosize: true
            };

            const config = {
                responsive: true,
                displayModeBar: false
            };

            Plotly.newPlot('cityChart', cityData, cityLayout, config);
        }

        // ==================== 数据表格 ====================
        function updateDataTable(data) {
            totalPages = Math.ceil(data.length / pageSize);
            document.getElementById('tableTotal').textContent = data.length;
            document.getElementById('totalPages').textContent = totalPages;
            renderTablePage();
        }

        function renderTablePage() {
            const tbody = document.getElementById('dataTableBody');
            const start = (currentPage - 1) * pageSize;
            const end = start + pageSize;
            const pageData = currentData.slice(start, end);

            if (pageData.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="8" style="text-align: center; padding: 40px; color: #a0aec0;">
                            暂无数据
                        </td>
                    </tr>
                `;
                return;
            }

            let html = '';
            pageData.forEach((item, index) => {
                const globalIndex = start + index + 1;
                const type = classifyEarthquake(item.magnitude);
                let badgeClass = 'weak';
                if (type === '有感地震') badgeClass = 'felt';
                if (type === '中强震') badgeClass = 'strong';

                html += `
                    <tr>
                        <td>${globalIndex}</td>
                        <td>${item.time.substring(0, 19)}</td>
                        <td>${item.city}</td>
                        <td>${item.location}</td>
                        <td><span class="magnitude-badge ${badgeClass}">${item.magnitude}级</span></td>
                        <td>${item.depth}</td>
                        <td>${type}</td>
                        <td><button class="view-btn" onclick="viewDetail(${start + index})">查看</button></td>
                    </tr>
                `;
            });

            tbody.innerHTML = html;
            document.getElementById('currentPage').textContent = currentPage;

            document.getElementById('firstPageBtn').disabled = currentPage === 1;
            document.getElementById('prevPageBtn').disabled = currentPage === 1;
            document.getElementById('nextPageBtn').disabled = currentPage === totalPages;
            document.getElementById('lastPageBtn').disabled = currentPage === totalPages;
        }

        function changePage(action) {
            switch(action) {
                case 'first':
                    currentPage = 1;
                    break;
                case 'prev':
                    if (currentPage > 1) currentPage--;
                    break;
                case 'next':
                    if (currentPage < totalPages) currentPage++;
                    break;
                case 'last':
                    currentPage = totalPages;
                    break;
            }
            renderTablePage();
        }

        function viewDetail(index) {
            const item = currentData[index];
            if (!item) return;

            const type = classifyEarthquake(item.magnitude);

            const tooltipContent = `
                <div class="tooltip-row"><span class="tooltip-label">时间:</span> ${item.time}</div>
                <div class="tooltip-row"><span class="tooltip-label">城市:</span> ${item.city}</div>
                <div class="tooltip-row"><span class="tooltip-label">位置:</span> ${item.location}</div>
                <div class="tooltip-row"><span class="tooltip-label">震级:</span> ${item.magnitude}级</div>
                <div class="tooltip-row"><span class="tooltip-label">深度:</span> ${item.depth}km</div>
                <div class="tooltip-row"><span class="tooltip-label">类型:</span> ${type}</div>
            `;

            const tooltip = document.getElementById('mapTooltip');
            tooltip.innerHTML = tooltipContent;

            const mapContainer = document.getElementById('mapPlot');
            const mapRect = mapContainer.getBoundingClientRect();

            const left = mapRect.width / 2 - 130;
            const top = 100;

            tooltip.style.left = left + 'px';
            tooltip.style.top = top + 'px';
            tooltip.className = 'map-tooltip show';

            setTimeout(() => {
                tooltip.className = 'map-tooltip';
            }, 5000);

            highlightPointOnMap(item);
        }

        function highlightPointOnMap(item) {
            if (currentMapMode === 'scatter' && leafletMap) {
                leafletMap.setView([item.latitude, item.longitude], 9);

                const highlightMarker = L.circleMarker([item.latitude, item.longitude], {
                    radius: 12,
                    fillColor: '#fff',
                    color: '#f56565',
                    weight: 3,
                    opacity: 1,
                    fillOpacity: 1
                }).addTo(leafletMap);

                highlightMarker.bindPopup(`
                    <div style="font-family: 'Microsoft YaHei', sans-serif;">
                        <strong style="font-size: 14px;">${item.location}</strong><br>
                        <div style="margin-top: 8px; line-height: 1.6;">
                            <b>时间:</b> ${item.time}<br>
                            <b>城市:</b> ${item.city}<br>
                            <b>震级:</b> ${item.magnitude}级<br>
                            <b>深度:</b> ${item.depth}km
                        </div>
                    </div>
                `).openPopup();

                currentMarkers.push(highlightMarker);

                setTimeout(() => {
                    leafletMap.removeLayer(highlightMarker);
                }, 3000);
            }
        }
    </script>
</body>
</html>
'''


def load_excel(file):
    """加载Excel文件"""
    try:
        df = pd.read_excel(file)
        original_columns = df.columns.tolist()
        logger.info(f"Excel文件读取成功,原始列名: {original_columns}")

        column_mapping = {
            '地震时间': 'time',
            '时间': 'time',
            '地震市区': 'city',
            '城市': 'city',
            '震中位置': 'location',
            '位置': 'location',
            '震级（单位级）': 'magnitude',
            '震级(单位:级)': 'magnitude',
            '震级': 'magnitude',
            '深度（单位公里）': 'depth',
            '深度(单位:公里)': 'depth',
            '深度': 'depth',
            '经度': 'longitude',
            '纬度': 'latitude'
        }

        renamed_columns = {}
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df.rename(columns={old_name: new_name}, inplace=True)
                renamed_columns[old_name] = new_name

        logger.info(f"已映射的列: {renamed_columns}")
        logger.info(f"映射后列名: {df.columns.tolist()}")

        required_columns = ['time', 'city', 'location', 'magnitude', 'depth', 'longitude', 'latitude']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            error_msg = f"缺少必需的列: {missing_columns}。原始列名: {original_columns}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        df['magnitude'] = pd.to_numeric(df['magnitude'], errors='coerce')
        df['depth'] = pd.to_numeric(df['depth'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['time'] = pd.to_datetime(df['time'], errors='coerce').astype(str)

        before_filter = len(df)
        df = df.dropna(subset=['longitude', 'latitude', 'magnitude'])
        after_filter = len(df)

        logger.info(f"数据过滤: {before_filter} -> {after_filter} 条记录")

        if after_filter == 0:
            raise ValueError("过滤后没有有效数据,请检查Excel文件中的数据是否正确")

        return df
    except Exception as e:
        logger.error(f"文件读取失败: {str(e)}", exc_info=True)
        return None


def call_ai_api(user_message):
    """调用智谱AI API"""
    if AI_API_KEY == "your_api_key_here":
        return {
            "success": False,
            "error": "请先配置AI API密钥。访问 https://open.bigmodel.cn/ 获取免费API密钥"
        }

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AI_API_KEY}"
        }

        system_prompt = """你是一个专业的地震知识助手。你的职责是回答用户关于地震、地震灾害、防震减灾等相关问题。
请用简洁、专业且易懂的语言回答问题。如果用户问的不是地震相关问题,请礼貌地引导他们询问地震相关内容。"""

        payload = {
            "model": "glm-4-flash",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }

        response = requests.post(AI_API_URL, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            return {"success": True, "response": ai_response}
        else:
            error_msg = f"API请求失败 (状态码: {response.status_code})"
            logger.error(f"{error_msg}: {response.text}")
            return {"success": False, "error": error_msg}

    except requests.exceptions.Timeout:
        return {"success": False, "error": "请求超时,请稍后再试"}
    except Exception as e:
        logger.error(f"AI API调用错误: {str(e)}", exc_info=True)
        return {"success": False, "error": f"服务暂时不可用: {str(e)}"}


@app.route('/')
def index():
    """主页面"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传Excel文件"""
    global earthquake_data

    try:
        if 'file' not in request.files:
            logger.error("请求中没有文件")
            return jsonify({'success': False, 'error': '没有文件'}), 400

        file = request.files['file']
        if file.filename == '':
            logger.error("文件名为空")
            return jsonify({'success': False, 'error': '文件名为空'}), 400

        logger.info(f"收到文件: {file.filename}")

        df = load_excel(file)
        if df is None:
            return jsonify({'success': False, 'error': '文件读取失败,请检查日志了解详情'}), 400

        if df.empty:
            return jsonify({'success': False, 'error': '文件中没有有效数据'}), 400

        earthquake_data = df
        cities = sorted(df['city'].dropna().unique().tolist())

        logger.info(f"成功加载 {len(df)} 条地震记录,包含 {len(cities)} 个城市")

        return jsonify({
            'success': True,
            'count': len(df),
            'cities': cities
        })

    except ValueError as ve:
        logger.error(f"数据验证错误: {str(ve)}")
        return jsonify({'success': False, 'error': str(ve)}), 400
    except Exception as e:
        logger.error(f"上传处理错误: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'服务器错误: {str(e)}'}), 500


@app.route('/api/data')
def get_data():
    """获取地震数据"""
    if earthquake_data.empty:
        return jsonify([])

    return jsonify(earthquake_data.to_dict('records'))


@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """AI聊天接口"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'success': False, 'error': '消息不能为空'})

        logger.info(f"收到AI请求: {user_message}")

        result = call_ai_api(user_message)

        if result['success']:
            logger.info(f"AI响应成功")
        else:
            logger.error(f"AI响应失败: {result.get('error', 'Unknown error')}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"AI聊天错误: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'处理失败: {str(e)}'})


@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    logger.info("客户端已连接")
    emit('status', {'message': '已连接到服务器'})


@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开"""
    logger.info("客户端已断开")


if __name__ == '__main__':
    print("""
    ==========================================
    广西地震灾害可视化系统启动中 (含AI助手)
    ==========================================

    访问地址: http://localhost:5000

    使用说明:
    1. 在浏览器中打开上述地址
    2. 上传包含地震数据的Excel文件
    3. 点击右上角"🤖 AI助手"按钮打开聊天窗口
    4. 向AI助手提问地震相关知识
    5. 点击"信息检索"按钮打开检索面板
    6. 设置查询条件后点击"查询"按钮
    7. 查看地震分布地图和统计图表
    8. 点击地图右上角按钮切换散点图/热力图
    9. 点击"播放"按钮开始时间轴动画

    AI助手配置:
    - 请在代码第27行填入你的智谱AI API密钥
    - 免费获取: https://open.bigmodel.cn/
    - 注册后可获得免费额度

    按 Ctrl+C 停止服务器
    ==========================================
    """)

    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
