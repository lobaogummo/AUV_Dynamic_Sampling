param(
  [int]$IntervalSeconds = 300,
  [string]$Remote = "origin",
  [string]$Branch = "",
  [switch]$Once,
  [switch]$AutoStash
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
  return (git rev-parse --show-toplevel 2>$null).Trim()
}

function Get-UpstreamRef {
  if ($Branch -and $Branch.Trim().Length -gt 0) {
    return "$Remote/$Branch"
  }
  return (git rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>$null).Trim()
}

function Is-WorkingTreeClean {
  $status = (git status --porcelain)
  return ($status.Count -eq 0)
}

function Write-Log([string]$Message) {
  $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  Write-Host "[$ts] $Message"
}

$repoRoot = Get-RepoRoot
if (-not $repoRoot) {
  throw "Nao foi possivel detectar um repositorio Git no diretorio atual."
}

Set-Location $repoRoot
Write-Log "Repo: $repoRoot"

$upstream = Get-UpstreamRef
if (-not $upstream) {
  throw "Nao foi possivel detectar upstream. Configure com: git branch --set-upstream-to=$Remote/<branch>"
}

if ($Once) {
  Write-Log "Verificando uma vez contra $upstream..."
} else {
  Write-Log "Monitorando $upstream a cada $IntervalSeconds segundos. Ctrl+C para parar."
}

while ($true) {
  try {
    git fetch --prune $Remote | Out-Null

    $head = (git rev-parse HEAD).Trim()
    $up = (git rev-parse $upstream).Trim()

    if ($head -ne $up) {
      $base = (git merge-base HEAD $upstream).Trim()
      if ($base -eq $head) {
        if (Is-WorkingTreeClean) {
          Write-Log "Novo commit detectado em $upstream. Fazendo pull (ff-only)..."
          git pull --ff-only | Out-Host
        } else {
          if ($AutoStash) {
            $stashName = "autostash $(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss')"
            Write-Log "Novo commit em $upstream. Salvando stash e fazendo pull (ff-only)..."
            git stash push -u -m $stashName | Out-Host
            git pull --ff-only | Out-Host
            Write-Log "Aplicando stash ($stashName)..."
            git stash pop | Out-Host
          } else {
            Write-Log "Novo commit em $upstream, mas ha alteracoes locais. Nao fiz pull. Use -AutoStash para tentar automaticamente."
          }
        }
      } elseif ($base -eq $up) {
        Write-Log "Seu branch local esta a frente de $upstream (sem pull)."
      } else {
        Write-Log "Branches divergiram (sem pull). Resolve manualmente: git pull --rebase (ou merge)."
      }
    }
  } catch {
    Write-Log "Erro: $($_.Exception.Message)"
  }

  if ($Once) { break }
  Start-Sleep -Seconds $IntervalSeconds
}
