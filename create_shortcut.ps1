$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("$env:USERPROFILE\Desktop\Focus Timer.lnk")
$s.TargetPath = "$env:USERPROFILE\Desktop\FocusTimer\start.vbs"
$s.WorkingDirectory = "$env:USERPROFILE\Desktop\FocusTimer"
$s.Description = "Focus Timer"
$s.Save()
