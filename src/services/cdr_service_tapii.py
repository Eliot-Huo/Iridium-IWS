"""
TAP II v9.2 CDR 解析服務
完全符合 Iridium Call Record Interface Definition 規範
固定長度 160 字元格式解析
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from zoneinfo import ZoneInfo


# ==================== TAP II 資料模型 ====================

@dataclass
class TAPIIHeader:
    """TAP II Header Record (Type 10)"""
    record_type: str  # 固定 "10"
    sender: str  # PLMN 代碼 (如 "USA77")
    recipient: str  # Service Provider 代碼
    file_sequence_number: str
    tax_treatment: str
    tax_rates: List[float]  # 最多 8 個稅率
    file_creation_date: str  # YYMMDD
    file_transmission_date: str  # YYMMDD
    transfer_cutoff_timestamp: str  # YYMMDDHHMMSS
    utc_time_offset: str  # ±HHMM
    specification_version: str  # "03" for TAP II v3.12
    international_access_code: List[str]  # 最多 2 個 IAC
    country_code: List[str]  # 最多 2 個國碼


@dataclass
class UTCTimeOffset:
    """UTC Time Offset Record (Type 14)"""
    record_type: str  # 固定 "14"
    offset_table: Dict[str, str]  # {'A': '+0800', 'B': '-0500', ...}
    
    def get_timezone(self, code: str) -> timezone:
        """
        根據 UTC Offset Code 獲取時區
        
        Args:
            code: 'A' to 'O'
            
        Returns:
            timezone 物件
        """
        offset_str = self.offset_table.get(code, '+0000')
        
        # 解析偏移量 (格式: ±HHMM)
        sign = 1 if offset_str[0] == '+' else -1
        hours = int(offset_str[1:3])
        minutes = int(offset_str[3:5])
        
        total_seconds = sign * (hours * 3600 + minutes * 60)
        return timezone(timedelta(seconds=total_seconds))


@dataclass
class MOCRecord:
    """Mobile Originated Call Record (Type 20)"""
    record_type: str  # 固定 "20"
    chain_reference: str  # 關聯到 Supplementary Service Record
    partial_indicator: str  # 空格=普通, 4=Credit Card, 6=Call Forward
    imsi: str  # 對於 SBD 填入 IMEI
    imei: str  # 對於 SBD 為空
    modification_indicator: str  # "1" 表示號碼已標準化
    type_of_number: str
    numbering_plan: str
    called_number: str  # 格式: 00+CountryCode+Number
    service_type: str  # 0=Voice/SMS, 1=Data, 2=PTT, 3=Messaging
    service_code: str  # 11=Voice, 36=SBD, 37=OpenPort, 40=Certus Voice 等
    dual_service_type: str
    dual_service_code: str  # 11=OpenPort, 46=GO, 47=ATS
    radio_channel_requested: str
    radio_channel_used: str
    transparency_indicator: str  # 0=Regular, 1=Alternate Rating
    ss_events: List[Tuple[str, str]]  # [(action_code, ss_code), ...] 最多 5 個
    msc_id: str  # "SATELLITE" 或 "CELLULAR"
    location_area_code: str  # E.212 Country Code (5 位)
    cell_id: str  # Iridium LAC (5 位)
    mobile_station_class_mark: str  # 1=In region, 2=Out region
    charging_date: str  # YYMMDD
    charge_start_time: str  # HHMMSS
    utc_time_offset_code: str  # 'A' to 'O'
    chargeable_units: int  # 秒數或資料量
    data_volume_reference: int  # 位元組數
    charge: float  # 金額 (3 位小數精度)
    charged_item: str  # 'D'=Duration, 'V'=Volume
    tax_rate_code: str
    exchange_rate_code: str
    originating_network: str  # 對於 Certus Data: 總秒數
    sdf_id: str  # Secondary Data Flow ID (Certus Data)


@dataclass
class MTCRecord:
    """Mobile Terminated Call Record (Type 30)"""
    record_type: str  # 固定 "30"
    chain_reference: str
    unused_1: str
    imsi: str
    imei: str
    modification_indicator: str
    type_of_number: str
    numbering_plan: str
    called_number: str  # 可能不包含 IAC
    service_type: str
    service_code: str
    dual_service_type: str
    dual_service_code: str
    radio_channel_requested: str
    radio_channel_used: str
    transparency_indicator: str
    ss_events: List[Tuple[str, str]]
    msc_id: str
    location_area_code: str
    cell_id: str
    mobile_station_class_mark: str
    charging_date: str
    charge_start_time: str
    utc_time_offset_code: str
    chargeable_units: int
    data_volume_reference: int
    charge: float
    charged_item: str
    tax_rate_code: str
    exchange_rate_code: str
    originating_network: str
    unused_2: str


@dataclass
class SupplementaryServiceRecord:
    """Mobile Supplementary Service Record (Type 40)"""
    record_type: str  # 固定 "40"
    chain_reference: str
    imsi: str
    imei: str
    basic_service_codes: str
    supplementary_service_code: str  # 81=Mailbox Check, 82=Registration, 50=Location Update 等
    action_code: str
    msc_identification: str
    location_area_code: str
    cell_id: str
    ms_class_mark: str
    charge_start_date: str
    charge_start_time: str
    utc_time_offset_code: str
    charge: float
    charged_item: str
    tax_rate_code: str
    exchange_rate_code: str
    ss_parameter: str
    unused: str


# ==================== TAP II 解析器 ====================

class TAPIIParser:
    """
    TAP II v9.2 格式解析器
    固定長度 160 字元記錄格式
    """
    
    # Service Code 對應表
    SERVICE_CODE_NAMES = {
        '11': 'Telephony Voice / OpenPort Voice',
        '15': 'PTT',
        '21': 'SMS MT',
        '22': 'SMS MO',
        '25': 'Dial Up Data',
        '26': 'Direct Internet Data',
        '27': 'M2M RUDICS Data',
        '36': 'SBD Data',
        '37': 'OpenPort Data',
        '38': 'M2M SBD Data',
        '40': 'Certus Voice',
        '41': 'Certus Data',
        '42': 'Certus Streaming',
        '43': 'Iridium Messaging Transport (IMT)',
    }
    
    # Supplementary Service Code 對應表
    SS_CODE_NAMES = {
        '81': 'SBD/M2M Mailbox Check',
        '82': 'SBD/M2M Registration',
        '50': 'GMDSS Location Update',
        '51': 'GMDSS Shoulder Tap',
        '52': 'GMDSS SMS Safety',
        '53': 'GMDSS Voice RCC Reroute',
        '21': 'Call Forwarding Unconditional',
        '29': 'Call Forwarding on Busy',
        '2A': 'Call Forwarding on No Reply',
        '2B': 'Call Forwarding on Not Reachable',
    }
    
    def __init__(self):
        self.utc_offset_table: Dict[str, str] = {}
        self.header: Optional[TAPIIHeader] = None
    
    def parse_file(self, filepath: str) -> Tuple[TAPIIHeader, List, UTCTimeOffset]:
        """
        解析完整的 TAP II 檔案
        
        Args:
            filepath: TAP II .dat 檔案路徑
            
        Returns:
            (Header, Records, UTC Offset Table)
        """
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        header = None
        utc_offset_record = None
        records = []
        
        for line in lines:
            if len(line.strip()) != 160:
                continue  # 跳過非標準長度的行
            
            record_type = line[0:2]
            
            if record_type == '10':
                header = self.parse_header(line)
            elif record_type == '14':
                utc_offset_record = self.parse_utc_offset(line)
                self.utc_offset_table = utc_offset_record.offset_table
            elif record_type == '20':
                records.append(self.parse_moc(line))
            elif record_type == '30':
                records.append(self.parse_mtc(line))
            elif record_type == '40':
                records.append(self.parse_supplementary_service(line))
            elif record_type == '90':
                # Trailer Record - 可以提取統計資訊
                pass
        
        return header, records, utc_offset_record
    
    def parse_header(self, line: str) -> TAPIIHeader:
        """解析 Header Record (Type 10)"""
        if len(line) != 160:
            raise ValueError(f"Invalid TAP II record length: {len(line)}, expected 160")
        
        # 提取 Tax Rates (最多 8 個，每個 4 位數)
        tax_rates = []
        for i in range(8):
            pos_start = 20 + i * 4
            pos_end = pos_start + 4
            rate_str = line[pos_start:pos_end].strip()
            if rate_str:
                tax_rates.append(float(rate_str) / 10000)  # 4 位小數精度
        
        # 提取 IAC (最多 2 個，每個 3 位)
        iac_list = []
        iac1 = line[96:99].strip()
        iac2 = line[99:102].strip()
        if iac1:
            iac_list.append(iac1)
        if iac2:
            iac_list.append(iac2)
        
        # 提取 Country Code (最多 2 個，每個 4 位)
        country_codes = []
        cc1 = line[108:112].strip()
        cc2 = line[112:116].strip()
        if cc1:
            country_codes.append(cc1)
        if cc2:
            country_codes.append(cc2)
        
        return TAPIIHeader(
            record_type=line[0:2],
            sender=line[2:7].strip(),
            recipient=line[7:12].strip(),
            file_sequence_number=line[12:19],
            tax_treatment=line[19],
            tax_rates=tax_rates,
            file_creation_date=line[65:71],
            file_transmission_date=line[71:77],
            transfer_cutoff_timestamp=line[77:89],
            utc_time_offset=line[89:94],
            specification_version=line[94:96],
            international_access_code=iac_list,
            country_code=country_codes
        )
    
    def parse_utc_offset(self, line: str) -> UTCTimeOffset:
        """解析 UTC Time Offset Record (Type 14)"""
        if len(line) != 160:
            raise ValueError(f"Invalid TAP II record length: {len(line)}")
        
        offset_table = {}
        
        # 最多 15 個 offset (每個 6 位元組: 1 code + 5 offset)
        for i in range(15):
            pos_start = 2 + i * 6
            code = line[pos_start]
            offset_str = line[pos_start+1:pos_start+6]
            
            if code == ' ':
                break  # 結束
            
            offset_table[code] = offset_str
        
        return UTCTimeOffset(
            record_type='14',
            offset_table=offset_table
        )
    
    def parse_moc(self, line: str) -> MOCRecord:
        """解析 Mobile Originated Call Record (Type 20)"""
        if len(line) != 160:
            raise ValueError(f"Invalid TAP II record length: {len(line)}")
        
        # 提取 SS Events (最多 5 個，每個 3 位元組)
        ss_events = []
        for i in range(5):
            pos_start = 73 + i * 3
            action_code = line[pos_start]
            ss_code = line[pos_start+1:pos_start+3]
            if action_code != ' ' or ss_code.strip():
                ss_events.append((action_code, ss_code))
        
        return MOCRecord(
            record_type=line[0:2],
            chain_reference=line[2:8].strip(),
            partial_indicator=line[8],
            imsi=line[9:24].strip(),
            imei=line[24:40].strip(),
            modification_indicator=line[40],
            type_of_number=line[41],
            numbering_plan=line[42],
            called_number=line[43:64].strip(),
            service_type=line[64],
            service_code=line[65:67],
            dual_service_type=line[67],
            dual_service_code=line[68:70],
            radio_channel_requested=line[70],
            radio_channel_used=line[71],
            transparency_indicator=line[72],
            ss_events=ss_events,
            msc_id=line[88:103].strip(),
            location_area_code=line[103:108],
            cell_id=line[108:113],
            mobile_station_class_mark=line[113],
            charging_date=line[114:120],
            charge_start_time=line[120:126],
            utc_time_offset_code=line[126],
            chargeable_units=int(line[127:133]),
            data_volume_reference=int(line[133:139]),
            charge=int(line[139:148]) / 1000.0,  # 3 位小數精度
            charged_item=line[148],
            tax_rate_code=line[149],
            exchange_rate_code=line[150],
            originating_network=line[151:157].strip(),
            sdf_id=line[157:160].strip()
        )
    
    def parse_mtc(self, line: str) -> MTCRecord:
        """解析 Mobile Terminated Call Record (Type 30)"""
        if len(line) != 160:
            raise ValueError(f"Invalid TAP II record length: {len(line)}")
        
        # 提取 SS Events
        ss_events = []
        for i in range(5):
            pos_start = 73 + i * 3
            action_code = line[pos_start]
            ss_code = line[pos_start+1:pos_start+3]
            if action_code != ' ' or ss_code.strip():
                ss_events.append((action_code, ss_code))
        
        return MTCRecord(
            record_type=line[0:2],
            chain_reference=line[2:8].strip(),
            unused_1=line[8],
            imsi=line[9:24].strip(),
            imei=line[24:40].strip(),
            modification_indicator=line[40],
            type_of_number=line[41],
            numbering_plan=line[42],
            called_number=line[43:64].strip(),
            service_type=line[64],
            service_code=line[65:67],
            dual_service_type=line[67],
            dual_service_code=line[68:70],
            radio_channel_requested=line[70],
            radio_channel_used=line[71],
            transparency_indicator=line[72],
            ss_events=ss_events,
            msc_id=line[88:103].strip(),
            location_area_code=line[103:108],
            cell_id=line[108:113],
            mobile_station_class_mark=line[113],
            charging_date=line[114:120],
            charge_start_time=line[120:126],
            utc_time_offset_code=line[126],
            chargeable_units=int(line[127:133]),
            data_volume_reference=int(line[133:139]),
            charge=int(line[139:148]) / 1000.0,
            charged_item=line[148],
            tax_rate_code=line[149],
            exchange_rate_code=line[150],
            originating_network=line[151:157].strip(),
            unused_2=line[157:160]
        )
    
    def parse_supplementary_service(self, line: str) -> SupplementaryServiceRecord:
        """解析 Supplementary Service Record (Type 40)"""
        if len(line) != 160:
            raise ValueError(f"Invalid TAP II record length: {len(line)}")
        
        return SupplementaryServiceRecord(
            record_type=line[0:2],
            chain_reference=line[2:8].strip(),
            imsi=line[8:23].strip(),
            imei=line[23:39].strip(),
            basic_service_codes=line[39:54].strip(),
            supplementary_service_code=line[54:56],
            action_code=line[56],
            msc_identification=line[57:72].strip(),
            location_area_code=line[72:77],
            cell_id=line[77:82],
            ms_class_mark=line[82],
            charge_start_date=line[83:89],
            charge_start_time=line[89:95],
            utc_time_offset_code=line[95],
            charge=int(line[96:105]) / 1000.0,
            charged_item=line[105],
            tax_rate_code=line[106],
            exchange_rate_code=line[107],
            ss_parameter=line[108:148].strip(),
            unused=line[148:160]
        )
    
    def parse_local_datetime(self, date_str: str, time_str: str, utc_code: str) -> datetime:
        """
        解析 TAP II 中的本地時間
        
        根據官方檔案：TAP II 中的時間已經是本地時間，不需要轉換
        
        Args:
            date_str: YYMMDD
            time_str: HHMMSS
            utc_code: UTC Time Offset Code ('A' to 'O')
            
        Returns:
            帶時區資訊的 datetime 物件
        """
        # 解析日期時間
        datetime_str = f"20{date_str} {time_str}"
        local_time = datetime.strptime(datetime_str, '%Y%m%d %H%M%S')
        
        # 根據 UTC Offset Code 獲取時區
        if utc_code in self.utc_offset_table:
            offset_str = self.utc_offset_table[utc_code]
            tz = self._parse_timezone(offset_str)
            local_time = local_time.replace(tzinfo=tz)
        
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
    
    def get_service_name(self, service_code: str) -> str:
        """取得服務名稱"""
        return self.SERVICE_CODE_NAMES.get(service_code, f'Unknown Service {service_code}')
    
    def get_ss_code_name(self, ss_code: str) -> str:
        """取得 Supplementary Service 名稱"""
        return self.SS_CODE_NAMES.get(ss_code, f'Unknown SS Code {ss_code}')


# ==================== 轉換為簡化模型 ====================

def convert_moc_to_simple_record(moc: MOCRecord, parser: TAPIIParser) -> dict:
    """
    將 TAP II MOC 記錄轉換為簡化的 CDR 記錄格式
    
    Args:
        moc: MOC 記錄
        parser: TAP II 解析器（含 UTC Offset Table）
        
    Returns:
        簡化的 CDR 字典
    """
    # 解析本地時間
    call_datetime = parser.parse_local_datetime(
        moc.charging_date,
        moc.charge_start_time,
        moc.utc_time_offset_code
    )
    
    # 轉換為台北時間
    taipei_tz = ZoneInfo('Asia/Taipei')
    call_datetime_taipei = call_datetime.astimezone(taipei_tz)
    
    return {
        'imei': moc.imsi if moc.service_code in ['36', '38'] else moc.imei,
        'imsi': moc.imsi,
        'call_datetime': call_datetime_taipei,
        'duration_seconds': moc.chargeable_units,
        'data_mb': moc.data_volume_reference / 1000000,  # 位元組轉 MB
        'call_type': parser.get_service_name(moc.service_code),
        'service_code': moc.service_code,
        'destination': moc.called_number,
        'cost': moc.charge,
        'location_country': moc.location_area_code,
        'cell_id': moc.cell_id,
        'msc_id': moc.msc_id,
        'timezone': 'Asia/Taipei'
    }


# ==================== 主要使用範例 ====================

def main():
    """測試 TAP II 解析器"""
    parser = TAPIIParser()
    
    # 測試解析單行 MOC 記錄
    test_moc_line = (
        "20                     901037030000020309006010009000"
        "10014807525100        11  1 SATELLITE     00310021941304"
        "60115231626A000045000000000000780D0A                  "
        "               "
    )
    
    try:
        # 解析 MOC
        moc = parser.parse_moc(test_moc_line)
        print(f"✅ MOC 解析成功")
        print(f"   IMSI: {moc.imsi}")
        print(f"   Service Code: {moc.service_code} ({parser.get_service_name(moc.service_code)})")
        print(f"   Called Number: {moc.called_number}")
        print(f"   Charge: ${moc.charge:.2f}")
        print(f"   Duration: {moc.chargeable_units} seconds")
        
    except Exception as e:
        print(f"❌ 解析失敗: {e}")


if __name__ == '__main__':
    main()
