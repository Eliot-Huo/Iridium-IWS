#!/bin/bash
# Git 提交準備腳本
# Prepare for Git Commit Script

echo "=================================="
echo "Git 提交準備檢查"
echo "=================================="

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 檢查函數
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1 存在"
        return 0
    else
        echo -e "${RED}✗${NC} $1 不存在"
        return 1
    fi
}

# 1. 檢查核心檔案
echo ""
echo "1. 檢查核心檔案..."
echo "----------------------------"

FILES=(
    "src/services/device_history.py"
    "src/services/enhanced_billing_calculator.py"
    "render_device_operations_page.py"
    "render_enhanced_billing_page.py"
    "app.py"
    "README.md"
    "requirements.txt"
    ".gitignore"
    "DEPLOYMENT_GUIDE.md"
    "GITHUB_DEPLOYMENT_CHECKLIST.md"
)

missing_files=0
for file in "${FILES[@]}"; do
    if ! check_file "$file"; then
        missing_files=$((missing_files + 1))
    fi
done

if [ $missing_files -gt 0 ]; then
    echo -e "${RED}❌ 有 $missing_files 個檔案缺失${NC}"
    exit 1
fi

# 2. 檢查敏感資訊
echo ""
echo "2. 檢查敏感資訊..."
echo "----------------------------"

if [ -f ".streamlit/secrets.toml" ]; then
    echo -e "${YELLOW}⚠${NC}  發現 .streamlit/secrets.toml"
    echo "    檢查是否在 .gitignore 中..."
    if grep -q "secrets.toml" .gitignore; then
        echo -e "${GREEN}✓${NC} secrets.toml 已在 .gitignore 中"
    else
        echo -e "${RED}✗${NC} secrets.toml 未在 .gitignore 中"
        exit 1
    fi
fi

# 檢查是否有意外的敏感檔案
echo "    檢查 JSON 金鑰檔案..."
if find . -name "*.json" -type f ! -path "*/node_modules/*" ! -path "*/__pycache__/*" | grep -q .; then
    echo -e "${YELLOW}⚠${NC}  發現 JSON 檔案："
    find . -name "*.json" -type f ! -path "*/node_modules/*" ! -path "*/__pycache__/*"
    echo "    請確認這些不是憑證檔案"
fi

# 3. 運行測試
echo ""
echo "3. 運行測試..."
echo "----------------------------"

if [ -f "quick_test.py" ]; then
    echo "    運行快速測試..."
    if python3 quick_test.py > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} 快速測試通過"
    else
        echo -e "${RED}✗${NC} 快速測試失敗"
        echo "    請運行: python3 quick_test.py 查看詳情"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠${NC}  quick_test.py 不存在，跳過測試"
fi

# 4. 檢查 Git 狀態
echo ""
echo "4. 檢查 Git 狀態..."
echo "----------------------------"

if [ -d ".git" ]; then
    echo "    Git repository 已初始化"
    
    # 檢查是否有未追蹤的重要檔案
    untracked=$(git ls-files --others --exclude-standard | grep -E "\.(py|md|txt|toml\.example)$" | wc -l)
    if [ $untracked -gt 0 ]; then
        echo -e "${YELLOW}⚠${NC}  有 $untracked 個未追蹤的檔案"
        git ls-files --others --exclude-standard | grep -E "\.(py|md|txt|toml\.example)$"
    else
        echo -e "${GREEN}✓${NC} 所有重要檔案都已追蹤"
    fi
else
    echo -e "${YELLOW}⚠${NC}  Git repository 未初始化"
    echo "    運行: git init"
fi

# 5. 統計資訊
echo ""
echo "5. 專案統計..."
echo "----------------------------"

echo "    Python 檔案數量: $(find . -name "*.py" -type f ! -path "*/__pycache__/*" | wc -l)"
echo "    總程式碼行數: $(find . -name "*.py" -type f ! -path "*/__pycache__/*" -exec wc -l {} + | tail -1 | awk '{print $1}')"
echo "    測試檔案數量: $(find . -name "test_*.py" -type f | wc -l)"

# 6. 生成提交訊息建議
echo ""
echo "6. 建議的提交訊息..."
echo "----------------------------"

cat << 'EOF'
feat: Add enhanced billing system v6.37.0

New Features:
- Device operations management page
- Enhanced billing calculator with smart logic
- Complete billing rules implementation
- Device history tracking system
- Administrative fee mechanism
- Prepayment recovery mechanism

Improvements:
- Optimized UI design and user experience
- Added detailed billing notes and explanations
- Complete test suite with edge cases

Tests:
- test_extreme_scenarios.py (5 extreme scenarios)
- test_system_integration.py (3 integration scenarios)
- quick_test.py (quick validation)

Documentation:
- Updated README.md
- Added DEPLOYMENT_GUIDE.md
- Added GITHUB_DEPLOYMENT_CHECKLIST.md
- Created comprehensive billing contracts

Breaking Changes:
- None

Migration Guide:
- Run: mkdir -p data
- Configure: .streamlit/secrets.toml
EOF

# 7. 最終檢查清單
echo ""
echo "=================================="
echo "最終檢查清單"
echo "=================================="

echo ""
echo "準備提交到 GitHub 前，請確認："
echo ""
echo "  [ ] 所有測試通過"
echo "  [ ] README.md 已更新"
echo "  [ ] requirements.txt 包含所有依賴"
echo "  [ ] .gitignore 正確設定"
echo "  [ ] secrets.toml.example 已創建"
echo "  [ ] 沒有敏感資訊在 Git 中"
echo "  [ ] 所有新檔案已添加"
echo ""

echo "=================================="
echo "下一步操作："
echo "=================================="
echo ""
echo "1. 添加檔案："
echo "   git add ."
echo ""
echo "2. 提交變更（使用上面建議的訊息）："
echo "   git commit -m \"feat: Add enhanced billing system v6.37.0\" -m \"詳細說明...\""
echo ""
echo "3. 設定遠端 repository（替換成您的）："
echo "   git remote add origin https://github.com/YOUR_USERNAME/sbd-management-system.git"
echo ""
echo "4. 推送到 GitHub："
echo "   git push -u origin main"
echo ""
echo "=================================="

echo -e "${GREEN}✅ 準備檢查完成！${NC}"
