"""
TAP II v9.2 CDR 解析器 - SBD 專用版本
針對實際 FTP 下載的 CDR 檔案格式優化
- 支援無換行符格式（連續 160 字元記錄）
- 專注於 SBD (Service Code 36)
- 保留其他服務類型的擴展性
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from zoneinfo import ZoneInfo


# ==================== 資料模型 ====================

@dataclass
class SBDRecord:
    """SBD 專用 CDR 記錄"""
    # 基本資訊
    imei: str  # SBD 設備 IMEI (15 位)
    momsn: int  # Mobile Originated Message Sequence Number
    
    # 時間資訊
    call_datetime: datetime  # 本地時間（已含時區資訊）
    utc_offset_code: str  # UTC Offset Code ('A'-'O')
    
    # 資料量與費用
    data_bytes: int  # 傳輸位元組數
    charge: float  # 費用（美元）
    
    # 位置資訊
    location_area_code: str  # E.212 Country Code (5 位)
    cell_id: str  # Iridium LAC (5 位)
    msc_id: str  # "SATELLITE" 或 "CELLULAR"
    
    # 原始記錄（用於除錯）
    raw_record: Optional[str] = None


@dataclass
class UTCTimeOffset:
    """UTC Time Offset Record"""
    code: str
    offset: str  # 格式: ±HHMM
    
    def get_timezone(self) -> timezone:
        """轉換為 Python timezone 物件"""
        sign = 1 if self.offset[0] == '+' else -1
        hours = int(self.offset[1:3])
        minutes = int(self.offset[3:5])
        total_seconds = sign * (hours * 3600 + minutes * 60)
        return timezone(timedelta(seconds=total_seconds))


# ==================== SBD 專用解析器 ====================

class SBDParser:
    """
    SBD 專用 TAP II 解析器
    針對實際 FTP 下載的 CDR 檔案格式優化
    """
    
    # Service Code 定義
    SERVICE_CODE_SBD = '36'
    SERVICE_CODE_M2M_SBD = '38'
    
    def __init__(self):
        self.utc_offset_table: Dict[str, str] = {}
        self.header: Optional[dict] = None
        self.exchange_rate: Optional[dict] = None
    
    def parse_file(self, filepath: str) -> List[SBDRecord]:
        """
        解析完整的 TAP II CDR 檔案
        
        Args:
            filepath: CDR 檔案路徑
            
        Returns:
            List[SBDRecord]: SBD 記錄列表
        """
        # 讀取檔案（無換行符格式）
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 按 160 字元分割記錄
        records = []
        for i in range(0, len(content), 160):
            if i + 160 <= len(content):
                record = content[i:i+160]
                records.append(record)
        
        # 解析各類記錄
        sbd_records = []
        
        for record in records:
            record_type = record[0:2]
            
            if record_type == '10':
                # Header Record
                self.header = self._parse_header(record)
            
            elif record_type == '12':
                # Exchange Rate Record
                self.exchange_rate = self._parse_exchange_rate(record)
            
            elif record_type == '14':
                # UTC Time Offset Record
                self._parse_utc_offset(record)
            
            elif record_type == '20':
                # MOC Record - 檢查是否為 SBD
                service_code = record[65:67]
                if service_code in [self.SERVICE_CODE_SBD, self.SERVICE_CODE_M2M_SBD]:
                    sbd_record = self._parse_sbd_moc(record)
                    if sbd_record:
                        sbd_records.append(sbd_record)
            
            elif record_type == '90':
                # Trailer Record - 可用於驗證
                self._parse_trailer(record)
        
        return sbd_records
    
    def _parse_header(self, record: str) -> dict:
        """解析 Header Record (Type 10)"""
        return {
            'sender': record[2:7].strip(),
            'recipient': record[7:12].strip(),
            'file_seq': record[12:19],
            'spec_version': record[94:96],
            'file_creation_date': record[65:71],
            'file_transmission_date': record[71:77],
            'cutoff_timestamp': record[77:89],
            'utc_offset': record[89:94],
            'iac': record[96:108].strip(),
            'country_code': record[108:116].strip()
        }
    
    def _parse_exchange_rate(self, record: str) -> dict:
        """解析 Exchange Rate Record (Type 12)"""
        # 提取第一個匯率
        code = record[2]
        rate = record[3:13].strip()
        exponent = record[13]
        
        return {
            'code': code,
            'rate': rate,
            'exponent': exponent
        }
    
    def _parse_utc_offset(self, record: str):
        """解析 UTC Time Offset Record (Type 14)"""
        # 最多 15 個 offset
        for i in range(15):
            pos = 2 + i * 6
            code = record[pos]
            offset = record[pos+1:pos+6]
            
            if code == ' ':
                break
            
            self.utc_offset_table[code] = offset
    
    def _parse_sbd_moc(self, record: str) -> Optional[SBDRecord]:
        """
        解析 SBD MOC 記錄
        
        Args:
            record: 160 字元的 TAP II 記錄
            
        Returns:
            SBDRecord 或 None
        """
        try:
            # 基本資訊
            imei = record[9:24].strip()  # SBD 的 IMEI 在 IMSI 欄位
            
            # Called Number 提取 MOMSN
            called_number = record[43:64].strip()
            momsn = self._extract_momsn(called_number)
            
            # 時間資訊
            charge_date = record[114:120]  # YYMMDD
            charge_time = record[120:126]  # HHMMSS
            utc_offset_code = record[126]
            
            call_datetime = self._parse_datetime(
                charge_date, 
                charge_time, 
                utc_offset_code
            )
            
            # 資料量與費用
            data_bytes = int(record[133:139])
            charge_int = int(record[139:148])
            charge = charge_int / 1000.0  # 3 位小數精度
            
            # 位置資訊
            msc_id = record[88:103].strip()
            location_area_code = record[103:108]
            cell_id = record[108:113]
            
            return SBDRecord(
                imei=imei,
                momsn=momsn,
                call_datetime=call_datetime,
                utc_offset_code=utc_offset_code,
                data_bytes=data_bytes,
                charge=charge,
                location_area_code=location_area_code,
                cell_id=cell_id,
                msc_id=msc_id,
                raw_record=record
            )
            
        except Exception as e:
            print(f"⚠️  解析 SBD MOC 失敗: {e}")
            return None
    
    def _parse_trailer(self, record: str) -> dict:
        """解析 Trailer Record (Type 90)"""
        total_records = int(record[19:25])
        total_charge_str = record[59:71]
        
        # 解析總費用
        if total_charge_str.startswith('+'):
            total_charge = int(total_charge_str[1:]) / 1000.0
        else:
            total_charge = int(total_charge_str) / 1000.0
        
        return {
            'total_records': total_records,
            'first_call_date': record[25:31],
            'first_call_time': record[31:37],
            'last_call_date': record[42:48],
            'last_call_time': record[48:54],
            'total_charge': total_charge
        }
    
    def _extract_momsn(self, called_number: str) -> Optional[int]:
        """
        從 Called Number 提取 MOMSN
        
        格式: 0088160127842
              ││││││└─────┘
              ││││││ MOMSN (5 位，可能有前導零)
              │││││└─ 1 (SBD Prefix)
              ││││└── 60 (SBD Service)
              │││└─── 8816 (Iridium Satellite)
              ││└──── 00 (IAC)
        
        Args:
            called_number: TAP II Called Number 欄位
            
        Returns:
            MOMSN 或 None
        """
        if called_number.startswith('00881601'):
            momsn_str = called_number[8:13]
            return int(momsn_str)
        return None
    
    def _parse_datetime(self, date_str: str, time_str: str, utc_code: str) -> datetime:
        """
        解析 TAP II 中的本地時間
        
        **重要**：根據官方檔案，TAP II 中的時間已經是本地時間，不需要轉換！
        
        Args:
            date_str: YYMMDD (如 '251223')
            time_str: HHMMSS (如 '031230')
            utc_code: UTC Offset Code ('A'-'O')
            
        Returns:
            datetime 物件（已含時區資訊）
        """
        # 1. 解析本地時間（不假設是 UTC）
        datetime_str = f"20{date_str} {time_str}"
        local_time = datetime.strptime(datetime_str, '%Y%m%d %H%M%S')
        
        # 2. 根據 UTC Offset Code 添加時區資訊
        if utc_code in self.utc_offset_table:
            offset_str = self.utc_offset_table[utc_code]
            tz = self._parse_timezone(offset_str)
            local_time = local_time.replace(tzinfo=tz)
        else:
            # 如果找不到對應的 UTC Offset，使用預設（不應該發生）
            print(f"⚠️  找不到 UTC Offset Code: {utc_code}")
            local_time = local_time.replace(tzinfo=timezone.utc)
        
        return local_time
    
    def _parse_timezone(self, offset_str: str) -> timezone:
        """
        解析時區偏移字串
        
        Args:
            offset_str: 格式 ±HHMM (如 '+0800', '-0500')
            
        Returns:
            timezone 物件
        """
        sign = 1 if offset_str[0] == '+' else -1
        hours = int(offset_str[1:3])
        minutes = int(offset_str[3:5])
        
        total_seconds = sign * (hours * 3600 + minutes * 60)
        return timezone(timedelta(seconds=total_seconds))


# ==================== 簡化格式轉換 ====================

def convert_to_simple_format(sbd_record: SBDRecord) -> dict:
    """
    將 SBD 記錄轉換為簡化的字典格式
    用於向後相容現有的 CDRService
    
    Args:
        sbd_record: SBD 記錄物件
        
    Returns:
        簡化的 CDR 字典
    """
    # 轉換為台北時間（如果需要）
    taipei_tz = ZoneInfo('Asia/Taipei')
    call_datetime_taipei = sbd_record.call_datetime.astimezone(taipei_tz)
    
    return {
        'imei': sbd_record.imei,
        'momsn': sbd_record.momsn,
        'call_datetime': call_datetime_taipei,
        'duration_seconds': 0,  # SBD 無通話時間
        'data_mb': sbd_record.data_bytes / 1_000_000,  # bytes → MB
        'call_type': 'SBD Data',
        'service_code': '36',
        'destination': f'MOMSN-{sbd_record.momsn}',
        'cost': sbd_record.charge,
        'location_country': sbd_record.location_area_code,
        'cell_id': sbd_record.cell_id,
        'msc_id': sbd_record.msc_id,
        'timezone': 'Asia/Taipei'
    }


# ==================== 使用範例 ====================

def main():
    """測試 SBD 解析器"""
    parser = SBDParser()
    
    # 測試檔案
    test_file = '/mnt/user-data/uploads/CD20USA77DDATA0021938.dat'
    
    print("=" * 70)
    print("SBD TAP II 解析器測試")
    print("=" * 70)
    print()
    
    try:
        # 解析檔案
        sbd_records = parser.parse_file(test_file)
        
        print(f"✅ 成功解析 {len(sbd_records)} 筆 SBD 記錄")
        print()
        
        # 顯示統計資訊
        if parser.header:
            print("📄 檔案資訊:")
            print(f"  Sender: {parser.header['sender']}")
            print(f"  Recipient: {parser.header['recipient']}")
            print(f"  File Seq: {parser.header['file_seq']}")
            print(f"  Spec Version: {parser.header['spec_version']}")
            print()
        
        # 顯示 UTC Offset Table
        if parser.utc_offset_table:
            print("🕐 UTC Offset Table:")
            for code, offset in sorted(parser.utc_offset_table.items()):
                print(f"  Code '{code}': {offset}")
            print()
        
        # 顯示前 3 筆 SBD 記錄
        print("📊 SBD 記錄詳情:")
        for i, record in enumerate(sbd_records[:3], 1):
            print(f"\n  --- 記錄 {i} ---")
            print(f"  IMEI: {record.imei}")
            print(f"  MOMSN: {record.momsn}")
            print(f"  時間: {record.call_datetime} ({record.utc_offset_code})")
            print(f"  資料量: {record.data_bytes} bytes")
            print(f"  費用: ${record.charge:.2f}")
            print(f"  位置: {record.location_area_code} / Cell {record.cell_id}")
            print(f"  連接: {record.msc_id}")
        
        # 計算總費用
        total_charge = sum(r.charge for r in sbd_records)
        total_bytes = sum(r.data_bytes for r in sbd_records)
        
        print(f"\n📈 統計摘要:")
        print(f"  總記錄數: {len(sbd_records)}")
        print(f"  總費用: ${total_charge:.2f}")
        print(f"  總資料量: {total_bytes} bytes ({total_bytes/1024:.2f} KB)")
        print()
        
        # 測試轉換為簡化格式
        print("🔄 簡化格式轉換測試:")
        if sbd_records:
            simple = convert_to_simple_format(sbd_records[0])
            print(f"  IMEI: {simple['imei']}")
            print(f"  MOMSN: {simple['momsn']}")
            print(f"  時間: {simple['call_datetime']}")
            print(f"  費用: ${simple['cost']:.2f}")
        
        print()
        print("=" * 70)
        print("✅ 測試完成")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
