#!/usr/bin/env python3
from __future__ import annotations
import os, platform, re, subprocess, json, time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Any

# ── Device Detection ──────────────────────────────────────────────

@dataclass
class DeviceInfo:
    brand: str = "unknown"
    manufacturer: str = "unknown"
    model: str = "unknown"
    device: str = "unknown"
    hardware: str = "unknown"
    board: str = "unknown"
    android_ver: str = "unknown"
    sdk: str = "unknown"
    ram_gb: float = 0.0
    refresh_hz: int = 60
    screen_w: int = 0
    screen_h: int = 0
    dpi: int = 0
    touch_hz: int = 0
    battery: int = 100
    load_avg: float = 0.0

    @property
    def name(self) -> str:
        b, m = self.brand.strip(), self.model.strip()
        if b.lower() in ("unknown", "") and m.lower() != "unknown": return m
        if m.lower() in ("unknown", ""): return b
        return f"{b} {m}".strip()

def _run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=8, check=False)
        return (r.stdout or r.stderr or "").strip()
    except: return ""

def _prop(k): return _run(["getprop", k]) or _run(["/system/bin/getprop", k])

def _ram():
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            for ln in f:
                if ln.startswith("MemTotal:"):
                    return round(int(ln.split()[1]) / (1024*1024), 1)
    except: pass
    return 0.0

def _hz():
    for p in ("/sys/class/graphics/fb0/mode", "/sys/class/drm/sde-crtc-0/mode"):
        try:
            t = open(p).read().lower()
            for h in (144,120,90,60):
                if str(h) in t: return h
        except: continue
    ds = _run(["dumpsys","display"])
    for h in (144,120,90):
        if re.search(rf"\b{h}\s*hz\b", ds, re.I): return h
    return 60

def _touch_hz():
    for p in ("/sys/class/input/input0/sampling_rate","/sys/class/input/input1/sampling_rate"):
        try: return int(float(open(p).read().strip()))
        except: continue
    return 0

def _battery():
    m = re.search(r"level:\s*(\d+)", _run(["dumpsys","battery"]))
    return int(m.group(1)) if m else 100

def _load():
    try: return round(os.getloadavg()[0], 2)
    except: return 0.0

def get_device(manual=None) -> DeviceInfo:
    if manual:
        return DeviceInfo(brand="manual", manufacturer="manual", model=manual, device=manual.replace(" ","_").lower())
    if not (os.path.isdir("/system") or _prop("ro.product.model")):
        return DeviceInfo(brand="demo", manufacturer="pc", model=platform.node() or "pc", android_ver="0")
    d = DeviceInfo(
        brand=_prop("ro.product.brand") or _prop("ro.product.vendor.brand"),
        manufacturer=_prop("ro.product.manufacturer"),
        model=_prop("ro.product.model"),
        device=_prop("ro.product.device"),
        hardware=_prop("ro.hardware"),
        board=_prop("ro.product.board"),
        android_ver=_prop("ro.build.version.release"),
        sdk=_prop("ro.build.version.sdk"),
        ram_gb=_ram(), refresh_hz=_hz(), touch_hz=_touch_hz(), battery=_battery(), load_avg=_load(),
    )
    wm = _run(["wm","size"]) or _run(["/system/bin/wm","size"])
    m = re.search(r"(\d{3,4})x(\d{3,4})", wm)
    if m: d.screen_w, d.screen_h = int(m.group(1)), int(m.group(2))
    dn = _run(["wm","density"]) or _run(["/system/bin/wm","density"])
    m2 = re.search(r"(\d+)\s*dpi", dn, re.I)
    if m2: d.dpi = int(m2.group(1))
    return d

# ── Benchmark & Performance ───────────────────────────────────────

@dataclass
class PerfData:
    cpu_ops: float = 0.0
    mem_mbps: float = 0.0
    cores: int = 1
    max_freq: float = 0.0
    gfx_ratio: float = 0.0
    bench_time: float = 0.0
    power_index: float = 0.0
    tier: str = "mid"
    throttled: str = "n"
    hw_score: float = 0.0
    gfx_index: float = 0.0
    latency: float = 0.0
    boost: float = 0.0
    def to_dict(self): return asdict(self)

_R1,_R2,_R3 = 120_000_000.0, 800.0, 2_500_000.0

def _bench_cpu(s):
    st,dl,n,op = time.perf_counter(), time.perf_counter()+s, 123456789, 0
    while time.perf_counter()<dl:
        n=(n*1103515245+12345)&0x7FFFFFFF; n^=n>>13; op+=1
    return op/max(time.perf_counter()-st,0.001)

def _bench_mem(s):
    sz=4*1024*1024
    try: a,b=bytearray(sz),bytearray(sz)
    except: return 0.0
    st,dl,tb=time.perf_counter(),time.perf_counter()+s,0
    while time.perf_counter()<dl:
        b[:]=a; a[0]=(a[0]+1)%256; tb+=sz*2
    return (tb/(1024*1024))/max(time.perf_counter()-st,0.001)

def _bench_gfx(s):
    st,dl,acc=time.perf_counter(),time.perf_counter()+s,0.0
    while time.perf_counter()<dl:
        for i in range(64): acc+=(i*1.41421356)**0.5
    return acc/max(time.perf_counter()-st,0.001)

def _cores():
    try: return os.cpu_count() or 1
    except: return 1

def _max_freq():
    mx=0.0
    try:
        for nm in os.listdir("/sys/devices/system/cpu"):
            if not nm.startswith("cpu") or nm=="cpufreq": continue
            pt=f"/sys/devices/system/cpu/{nm}/cpufreq/cpuinfo_max_freq"
            if os.path.isfile(pt):
                with open(pt) as f: mx=max(mx,int(f.read().strip())/1000.0)
    except: pass
    return mx

def _hw_score(d: DeviceInfo):
    s=50.0
    if d.touch_hz>=240: s+=18
    elif d.touch_hz>=120: s+=10
    if d.refresh_hz>=120: s+=8
    if d.battery>=50: s+=5
    if d.battery<20: s-=12
    if d.load_avg>4.0: s-=10
    elif d.load_avg>2.5: s-=5
    return max(0.0,min(100.0,s))

def _tier_str(v):
    if v>=78: return "flagship"
    if v>=58: return "upper_mid"
    if v>=38: return "mid"
    return "budget"

def _chip_tier(hw, board, model_str):
    pt = Path(__file__).resolve().parent / "d8f.json"
    if not pt.is_file(): return "mid"
    ch = json.loads(pt.read_text(encoding="utf-8"))
    hay = f"{hw} {board} {model_str}".lower()
    order = ["flagship","upper_mid","mid","budget"]
    best = "mid"
    for cp,tr in ch.items():
        if cp in hay and order.index(tr) > order.index(best): best=tr
    return best

def _power_index(cpu,mem,gfx,n,xf,gp,gb):
    cs=min(100.0,(cpu/_R1)*100.0)
    ms=min(100.0,(mem/_R2)*100.0)
    gs=min(100.0,(gfx/_R3)*100.0)
    cb=min(12.0,max(0,(n-4)*2.5))
    mb=min(15.0,(xf-1500)/50.0) if xf>0 else 0.0
    return min(100.0, cs*0.42+ms*0.22+gs*0.12+cb+mb+gp*0.18+gb*0.06)

def run_benchmark(d: DeviceInfo, cs=2.0, ms=1.2, gs=0.9, runs=3) -> PerfData:
    n,xf = _cores(), _max_freq()
    ca,ma,ga=[],[],[]
    for _ in range(max(1,runs)):
        ca.append(_bench_cpu(cs)); ma.append(_bench_mem(ms)); ga.append(_bench_gfx(gs))
    cpu=sum(ca)/len(ca); mem=sum(ma)/len(ma); gfx=sum(ga)/len(ga)
    gp=_hw_score(d); gb=8.0 if d.battery>=40 and d.load_avg<2.0 else 0.0
    ix=_power_index(cpu,mem,gfx,n,xf,gp,gb)
    c2=_bench_cpu(0.7)
    th="t" if c2<cpu*0.72 else "n"
    if th=="t": ix*=0.9
    lat=max(4.0,1000.0/d.touch_hz) if d.touch_hz>0 else 16.0
    return PerfData(cpu_ops=round(cpu,0),mem_mbps=round(mem,1),cores=n,max_freq=round(xf,0),
        gfx_ratio=round(gfx,0),bench_time=round(cs*runs+ms+gs+0.7,1),
        power_index=round(ix,1),tier=_tier_str(ix),throttled=th,
        hw_score=round(gp,1),gfx_index=round(gfx/max(cpu,1)*1000,2),
        latency=round(lat,2),boost=round(gb,1))

# ── Sensitivity Generator ─────────────────────────────────────────

MX,MN = 200,1
SCOPE_KEYS = ("g","rd","x2","x4","sn","fl")
SCOPE_NAMES = {"g":"General","rd":"Red Dot","x2":"2x Scope","x4":"4x Scope","sn":"Sniper","fl":"Free Look"}
SCOPE_RATIO = {"rd":0.91,"x2":0.83,"x4":0.73,"sn":0.67,"fl":0.94}

def _clamp(v, lo=MN, hi=MX): return max(lo,min(hi,int(round(v))))

def _screen_diag(d: DeviceInfo):
    w,h=d.screen_w,d.screen_h
    if w<=0 or h<=0: return 2400.0,1.0
    dg=(w*w+h*h)**0.5
    return dg,(d.dpi or 400)/400.0

def _base_sensi(d: DeviceInfo, p: PerfData, tier: str):
    an={"budget":98,"mid":122,"upper_mid":148,"flagship":175}
    b=an.get(tier,122)
    b+=(p.power_index-50)*0.92
    hz={60:0,90:9,120:16,144:20}.get(d.refresh_hz or 60,0); b+=hz
    dg,df=_screen_diag(d)
    if dg>=2600: b-=10
    elif dg>=2350: b-=5
    elif dg<2000: b+=5
    b-=(df-1.0)*11
    if d.ram_gb>0:
        if d.ram_gb<4: b-=14
        elif d.ram_gb<6: b-=7
        elif d.ram_gb>=12: b+=8
    if p.throttled=="t": b-=9
    if p.max_freq>2800: b+=7
    elif 0<p.max_freq<1800: b-=7
    if 0<p.latency<8.0: b+=6
    elif p.latency>12.0: b-=4
    b+=p.boost*0.35; b+=p.hw_score*0.12
    return b

def _hs_bonus(d: DeviceInfo, p: PerfData, tier: str):
    hs=0.0
    if p.power_index>=55 and tier in ("upper_mid","flagship"): hs+=6.0
    if 0<p.latency<=10.0: hs+=4.0
    if d.refresh_hz>=90: hs+=3.0
    return hs

def _best_tier(d: DeviceInfo, p: PerfData):
    sc=_chip_tier(d.hardware, d.board, f"{d.hardware} {d.board} {d.model}")
    order=["budget","mid","upper_mid","flagship"]
    return order[max(order.index(p.tier), order.index(sc))]

def generate_sensitivity(d: DeviceInfo, p: PerfData):
    tier=_best_tier(d,p)
    gr=_clamp(_base_sensi(d,p,tier)+_hs_bonus(d,p,tier))
    sx={"g":gr}
    for k,r in SCOPE_RATIO.items(): sx[k]=_clamp(gr*r)
    sx["rd"]=_clamp(min(sx["rd"],gr-6))
    sx["x2"]=_clamp(min(sx["x2"],sx["rd"]-9))
    sx["x4"]=_clamp(min(sx["x4"],sx["x2"]-11))
    sx["sn"]=_clamp(min(sx["sn"],sx["x4"]-9))
    sx["fl"]=_clamp(max(sx["fl"],gr-14))
    if p.power_index>=60: sx["rd"]=_clamp(min(sx["rd"]+2,gr-4))
    return {"sx":sx,"tier":tier,"power_index":p.power_index,"max":MX,"hs_mode":_hs_bonus(d,p,tier)>0}

def device_from_json(json_str: str) -> DeviceInfo:
    """Build a DeviceInfo from the JSON auto-collected by Android (DeviceCollector.java)."""
    data = json.loads(json_str)
    return DeviceInfo(
        brand=data.get("brand","unknown"),
        manufacturer=data.get("manufacturer","unknown"),
        model=data.get("model","unknown"),
        device=data.get("device","unknown"),
        hardware=data.get("hardware","unknown"),
        board=data.get("board","unknown"),
        android_ver=data.get("android_ver","unknown"),
        sdk=str(data.get("sdk","unknown")),
        ram_gb=float(data.get("ram_gb",0.0)),
        refresh_hz=int(data.get("refresh_hz",60)) or 60,
        screen_w=int(data.get("screen_w",0)),
        screen_h=int(data.get("screen_h",0)),
        dpi=int(data.get("dpi",0)),
        touch_hz=int(data.get("touch_hz",0)),
        battery=int(data.get("battery",100)),
        load_avg=float(data.get("load_avg",0.0)),
    )

def run_full(device_json: str) -> str:
    """
    Single entry point called from the Android app.
    Takes auto-collected device JSON, runs the in-process benchmark,
    generates sensitivity, and returns the formatted report string.
    """
    d = device_from_json(device_json)
    p = run_benchmark(d, cs=1.0, ms=0.7, gs=0.5, runs=2)  # lighter benchmark for mobile UI responsiveness
    r = generate_sensitivity(d, p)
    return format_result(d, r, p)

def format_result(d: DeviceInfo, r: dict, p: PerfData) -> str:
    sx=r["sx"]
    lines=[
        "="*50,
        "  PRIME SHANI SENSI GENERATOR",
        "  Optimized For Your Device",
        f"  Scale: 1-{MX}",
        "="*50,
        f"DEVICE : {d.name}",
        f"CHIP   : {d.hardware} / {d.board}",
        f"PANEL  : {d.screen_w}x{d.screen_h} @{d.refresh_hz}Hz {d.dpi}dpi",
        f"RAM    : {d.ram_gb or '?'}GB | BATT {d.battery}% | LOAD {d.load_avg}",
        f"TOUCH  : {d.touch_hz or '?'}Hz | LAT {p.latency}ms",
        f"POWER  : {p.power_index}/100 | GFXIDX {p.gfx_index} | BOOST {p.boost}",
        f"TIER   : {r['tier']} | HS_MODE {'ON' if r['hs_mode'] else 'OFF'}",
        "",
        "--- IN-GAME SENSITIVITY ---",
    ]
    for k in SCOPE_KEYS:
        lines.append(f"{SCOPE_NAMES[k]:18}: {sx[k]}")
    lines.append("="*50)
    return "\n".join(lines)
