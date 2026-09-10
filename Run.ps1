while ($true) {
    Write-Host "Starting script at $(Get-Date)..."
#Please change the networks according to the available networks..
$networks = @("A", "Salim pasa") 

foreach ($wifi in $networks) {
    Write-Host "Connecting to $wifi..."
    netsh wlan connect name="$wifi"
    Start-Sleep -Seconds 5
#Please chabe the path to the bot accordingly
    python "C:\Specialized study\Bots\bot_final.py"
    
}

    

    Write-Host "Script exited. Restarting in 21 seconds..."
    Start-Sleep -Seconds 5
}