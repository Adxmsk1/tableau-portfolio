# opens a workbook in tableau and screenshots its windows (handy for checking layouts)
param([string]$Workbook, [string]$OutPrefix, [int]$Wait = 45, [switch]$KeepOpen)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
if (-not ('TabWin' -as [type])) {
Add-Type @"
using System; using System.Collections.Generic; using System.Runtime.InteropServices; using System.Text;
public class TabWin {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint f);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  public struct RECT { public int L, T, R, B; }
  public static List<IntPtr> ForPid(uint pid) {
    var list = new List<IntPtr>();
    EnumWindows((h, l) => { uint p; GetWindowThreadProcessId(h, out p); if (p == pid && IsWindowVisible(h)) list.Add(h); return true; }, IntPtr.Zero);
    return list;
  }
  public static string Title(IntPtr h) { var s = new StringBuilder(512); GetWindowText(h, s, 512); return s.ToString(); }
}
"@
}
[TabWin]::SetProcessDPIAware() | Out-Null
$exe = 'C:\Program Files\Tableau\Tableau 2026.2\bin\tableau.exe'
Get-Process tableau -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 2
$p = Start-Process $exe -ArgumentList "`"$Workbook`"" -PassThru
Start-Sleep $Wait
# print + close any error dialogs so they don't block the screenshot
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
if (-not ('TabMsg' -as [type])) {
Add-Type 'using System; using System.Runtime.InteropServices; public class TabMsg { [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l); }'
}
for ($k = 0; $k -lt 40; $k++) {
    $all = [TabWin]::ForPid([uint32]$p.Id) | Where-Object { [TabWin]::Title($_) -ne 'Tableau' -and [TabWin]::Title($_) -notmatch '^Tableau - ' }
    # leave the progress windows alone, closing them cancels the load
    if ($all | Where-Object { [TabWin]::Title($_) -match '^Opening workbook|^Processing Request|^$' }) { Start-Sleep 5; continue }
    if (-not ([TabWin]::ForPid([uint32]$p.Id) | Where-Object { [TabWin]::Title($_) -match '^Tableau - ' })) {
        if (-not ($all | Where-Object { [TabWin]::Title($_) -eq 'Unable to complete action' })) { Start-Sleep 5; continue }
    }
    $dlg = $all | Select-Object -First 1
    if (-not $dlg) { break }
    try {
        $el = [System.Windows.Automation.AutomationElement]::FromHandle($dlg)
        $names = $el.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition) |
            ForEach-Object {
                $v = $null
                try { $v = $_.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value } catch {}
                if (-not $v) { try { $v = $_.GetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern).DocumentRange.GetText(2000) } catch {} }
                if ($v) { $v } else { $_.Current.Name }
            } | Where-Object { $_ -and $_ -notin @('OK', 'Do not show again', 'Close') }
        "DIALOG [$([TabWin]::Title($dlg))]: $(($names | Select-Object -Unique) -join ' | ')"
    } catch { "DIALOG [$([TabWin]::Title($dlg))]: (text unreadable)" }
    [TabMsg]::PostMessage($dlg, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null  # WM_CLOSE
    Start-Sleep 3
}
Start-Sleep 20   # give the views time to draw
$i = 0
foreach ($h in [TabWin]::ForPid([uint32]$p.Id)) {
    $r = New-Object TabWin+RECT; [TabWin]::GetWindowRect($h, [ref]$r) | Out-Null
    $w = $r.R - $r.L; $hh = $r.B - $r.T
    if ($w -lt 50 -or $hh -lt 50) { continue }
    $bmp = New-Object System.Drawing.Bitmap $w, $hh
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $dc = $g.GetHdc(); [TabWin]::PrintWindow($h, $dc, 2) | Out-Null; $g.ReleaseHdc($dc); $g.Dispose()
    $f = "$OutPrefix-$i.png"; $bmp.Save($f, [System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
    "$f  [$([TabWin]::Title($h))] ${w}x$hh"
    $i++
}
if (-not $KeepOpen) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
