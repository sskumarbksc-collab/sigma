# Real-Time Yahoo Finance NSE Live Streamer for Local Browser & Cloud Sync
$ErrorActionPreference = "SilentlyContinue"

$symbols = @(
    "^NSEI","^NSEBANK",
    "RELIANCE","HDFCBANK","ICICIBANK","INFY","TCS","ITC","SBIN","BHARTIARTL",
    "LT","KOTAKBANK","AXISBANK","BAJFINANCE","HINDUNILVR","MARUTI","M&M",
    "SUNPHARMA","TITAN","ULTRACEMCO","NTPC","BAJAJFINSV","POWERGRID","TATASTEEL",
    "NESTLEIND","ADANIENT","ADANIPORTS","JSWSTEEL","HCLTECH","TECHM","WIPRO",
    "COALINDIA","ONGC","GRASIM","HINDALCO","INDUSINDBK","BAJAJ-AUTO","CIPLA",
    "DRREDDY","EICHERMOT","APOLLOHOSP","DIVISLAB","TATACONSUM","SBILIFE",
    "HDFCLIFE","BRITANNIA","HEROMOTOCO","BPCL","SHRIRAMFIN","BEL","TRENT","HAL","DLF"
)

$targetDirs = @(
    "C:\Users\sskum\.gemini\antigravity\scratch\nse-alpha-pro\static",
    "C:\NSE_ALPHA_15_PRO\static",
    "C:\Users\sskum\Desktop\NSE_ALPHA_15_PRO\static",
    "C:\Users\sskum\OneDrive\NSE_ALPHA_15_PRO\static"
)

function Fetch-AllYahooQuotes {
    $indices = @{}
    $stocks = @{}
    $exTimeStr = (Get-Date).ToString("HH:mm:ss")

    foreach ($s in $symbols) {
        try {
            $q = if ($s.StartsWith("^")) { $s } else { "$s.NS" }
            $u = "https://query1.finance.yahoo.com/v8/finance/chart/$([uri]::EscapeDataString($q))?interval=5m&range=1d"
            $res = Invoke-RestMethod -Uri $u -Headers @{"User-Agent"="Mozilla/5.0"} -TimeoutSec 3
            $r0 = $res.chart.result[0]
            $meta = $r0.meta
            $ltp = [math]::Round([double]$meta.regularMarketPrice, 2)
            $prev = [math]::Round([double]$meta.chartPreviousClose, 2)
            if ($ltp -le 0) { continue }
            $chg = [math]::Round((($ltp - $prev) / [math]::Max(1.0, $prev)) * 100.0, 2)

            if ($meta.regularMarketTime) {
                $dt = [DateTimeOffset]::FromUnixTimeSeconds([long]$meta.regularMarketTime).ToOffset([TimeSpan]::FromHours(5.5))
                $exTimeStr = $dt.ToString("HH:mm:ss")
            }

            if ($s.StartsWith("^")) {
                $indices[$s] = @{ ltp = $ltp; prev = $prev; change_pct = $chg }
            } else {
                $tsArr = $r0.timestamp
                $qObj = $r0.indicators.quote[0]
                $candles = @()
                if ($tsArr -and $qObj.close) {
                    $startIdx = [math]::Max(0, $tsArr.Count - 45)
                    for ($i = $startIdx; $i -lt $tsArr.Count; $i++) {
                        if ($null -ne $qObj.close[$i] -and $null -ne $qObj.open[$i]) {
                            $cdt = [DateTimeOffset]::FromUnixTimeSeconds([long]$tsArr[$i]).ToOffset([TimeSpan]::FromHours(5.5))
                            $candles += @{
                                time = $cdt.ToString("HH:mm")
                                open = [math]::Round([double]$qObj.open[$i], 2)
                                high = [math]::Round([double]$qObj.high[$i], 2)
                                low  = [math]::Round([double]$qObj.low[$i], 2)
                                close = [math]::Round([double]$qObj.close[$i], 2)
                            }
                        }
                    }
                }
                $stocks[$s] = @{
                    ltp = $ltp
                    prev = $prev
                    change_pct = $chg
                    candles = $candles
                }
            }
        } catch {}
    }

    $payload = @{
        exchange_time = $exTimeStr
        indices = $indices
        stocks = $stocks
    } | ConvertTo-Json -Depth 6 -Compress

    $jsContent = "window.__LIVE_NSE_DATA__ = $payload;"
    foreach ($dir in $targetDirs) {
        if (Test-Path $dir) {
            Set-Content -Path "$dir\live_nse_data.js" -Value $jsContent -Encoding UTF8 -Force
        }
    }
}

# Run first pass and signal completion
Fetch-AllYahooQuotes
Write-Output "FIRST_YAHOO_SYNC_COMPLETE"

# Continuous live loop during market hours
while ($true) {
    Start-Sleep -Seconds 3
    Fetch-AllYahooQuotes
}
