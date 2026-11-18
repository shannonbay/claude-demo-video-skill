# rec.ps1 — native-resolution screen recording of one fixed box (Windows, ffmpeg ddagrab).
#
#   rec.ps1 monitors                                   list monitors in physical pixels
#   rec.ps1 place  -X 2680 -Y -184 [-W 1920 -H 1080] [-Apps chrome,WindowsTerminal]
#                                                      put each app's main window exactly on the box
#   rec.ps1 grab   -X .. -Y .. [-Adapter 0 -Output 0]  one PNG of the box (check it before recording)
#   rec.ps1 start <name> -X .. -Y .. [-Adapter 0 -Output 0]   record shots\<name>.ts
#   rec.ps1 stop                                       stop the recording
#   rec.ps1 mark "<text>"                              timestamped note in shots\marks.txt
#
# X/Y are physical desktop coordinates of the box's top-left. ddagrab wants them relative to its
# monitor, so the script subtracts the monitor's origin (the monitor containing X,Y).
# Adapter/Output: the GPU and its output index of that monitor (a second GPU is adapter 1).
# Output dir: -Dir (default .\shots). ffmpeg: on PATH, or $env:FFMPEG.
param([Parameter(Position = 0)][string]$Cmd, [Parameter(Position = 1)][string]$Arg = '',
      [int]$X = 0, [int]$Y = 0, [int]$W = 1920, [int]$H = 1080, [int]$Adapter = 0, [int]$Output = 0,
      [string[]]$Apps = @('chrome', 'WindowsTerminal'), [string]$Dir = (Join-Path (Get-Location) 'shots'),
      [int]$Fps = 30)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force $Dir | Out-Null
$pidFile = Join-Path $Dir 'rec.pid'; $marks = Join-Path $Dir 'marks.txt'
$ff = if ($env:FFMPEG) { $env:FFMPEG } else { (Get-Command ffmpeg).Source }
if (-not ('RecWin' -as [type])) { Add-Type @'
using System; using System.Runtime.InteropServices; using System.Collections.Generic;
public static class RecWin {
  [DllImport("user32.dll")] public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr c);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("dwmapi.dll")] public static extern int DwmGetWindowAttribute(IntPtr h, int a, out RECT r, int s);
  public delegate bool MonEnum(IntPtr m, IntPtr dc, ref RECT r, IntPtr d);
  [DllImport("user32.dll")] public static extern bool EnumDisplayMonitors(IntPtr dc, IntPtr clip, MonEnum f, IntPtr d);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  public static List<RECT> Mons() { var l = new List<RECT>(); EnumDisplayMonitors(IntPtr.Zero, IntPtr.Zero, (IntPtr m, IntPtr dc, ref RECT r, IntPtr d) => { l.Add(r); return true; }, IntPtr.Zero); return l; }
}
'@ }
[RecWin]::SetThreadDpiAwarenessContext([IntPtr](-4)) | Out-Null   # per-monitor aware: physical pixels

function Mark($t) { "$((Get-Date).ToString('HH:mm:ss')) $t" | Add-Content -Encoding utf8 $marks }
function MonitorOf($px, $py) {
  foreach ($m in [RecWin]::Mons()) { if ($px -ge $m.L -and $px -lt $m.R -and $py -ge $m.T -and $py -lt $m.B) { return $m } }
  throw "no monitor contains $px,$py (see: rec.ps1 monitors)"
}
function Grab([string]$extra, [string]$out) {
  $m = MonitorOf $X $Y
  $src = "ddagrab=output_idx=$($Output):framerate=$($Fps):draw_mouse=1:offset_x=$($X - $m.L):offset_y=$($Y - $m.T):video_size=$($W)x$($H),hwdownload,format=bgra"
  "-hide_banner -loglevel error -y -init_hw_device d3d11va=dx:$Adapter -filter_hw_device dx -filter_complex `"$src`" $extra `"$out`""
}

switch ($Cmd) {
  'monitors' { [RecWin]::Mons() | % { "monitor at $($_.L),$($_.T)  $($_.R - $_.L)x$($_.B - $_.T)" } }
  'place' {
    $hs = Get-Process $Apps -ErrorAction SilentlyContinue | ? { $_.MainWindowHandle -ne 0 } | % { $_.MainWindowHandle }
    foreach ($h in $hs) {
      [RecWin]::ShowWindow($h, 9) | Out-Null
      [RecWin]::SetWindowPos($h, [IntPtr]::Zero, $X, $Y, $W, $H, 0x0014) | Out-Null
      $e = New-Object RecWin+RECT; [RecWin]::DwmGetWindowAttribute($h, 9, [ref]$e, 16) | Out-Null
      # correct for the invisible borders so the *visible* frame is exactly the box
      [RecWin]::SetWindowPos($h, [IntPtr]::Zero, $X - ($e.L - $X), $Y - ($e.T - $Y), 2 * $W - ($e.R - $e.L), 2 * $H - ($e.B - $e.T), 0x0014) | Out-Null
      [RecWin]::DwmGetWindowAttribute($h, 9, [ref]$e, 16) | Out-Null
      "$h -> visible $($e.L),$($e.T) $($e.R - $e.L)x$($e.B - $e.T)"
    }
  }
  'grab' {
    $out = Join-Path $Dir 'check.png'
    Start-Process $ff -ArgumentList (Grab '-frames:v 1' $out) -NoNewWindow -Wait; "frame: $out"
  }
  'start' {
    if (-not $Arg) { throw 'usage: rec.ps1 start <name> -X .. -Y ..' }
    if (Test-Path $pidFile) { throw "already recording (pid $(Get-Content $pidFile))" }
    $out = Join-Path $Dir "$Arg.ts"   # MPEG-TS: still playable after a hard stop
    $p = Start-Process $ff -ArgumentList (Grab '-c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p -g 60 -f mpegts' $out) -WindowStyle Hidden -PassThru
    $p.Id | Set-Content $pidFile; Mark "START $Arg"; "recording $out (pid $($p.Id))"
  }
  'stop' {
    if (-not (Test-Path $pidFile)) { 'not recording'; break }
    Stop-Process -Id (Get-Content $pidFile) -Force -ErrorAction SilentlyContinue
    Remove-Item $pidFile; Mark 'STOP'; 'stopped'
  }
  'mark' { Mark $Arg; 'marked' }
  default { Get-Content $PSCommandPath -TotalCount 14 | Select-Object -Skip 1 | % { $_.TrimStart('#') } }
}
