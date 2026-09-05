param([string]$Master='tamil-batch001.tex',[int]$Passes=2,[ValidateSet('xelatex','lualatex')][string]$Engine='xelatex',[ValidateSet('batchmode','nonstopmode')][string]$Interaction='batchmode',[ValidateRange(1000,60000)][int]$AcquisitionTimeoutMs=60000,[switch]$BibTeX,[string]$ReceiptName='TEX-B001-RECEIPT',[string]$StateDirectory=$PSScriptRoot)
$ErrorActionPreference='Stop'
$build=$PSScriptRoot
$state=[IO.Path]::GetFullPath($StateDirectory)
if(-not (Test-Path -LiteralPath $state -PathType Container)){throw 'State directory does not exist'}
if ($Master -notmatch '^[a-zA-Z0-9_-]+\.tex$') { throw 'Unsafe master filename' }
if ($Passes -lt 1 -or $Passes -gt 4) { throw 'Invalid pass count' }
if ($ReceiptName -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Unsafe receipt name' }
if ($BibTeX -and $Passes -lt 3) { throw 'Bibliography build requires at least three engine passes' }
$mutex=New-Object Threading.Mutex($false,'Global\InterlanguageTeXSlotV1')
$owned=$false
$abandoned=$false
$receipt=[ordered]@{schema='openlogic-tamil-tex-guard/1';mutex='Global\InterlanguageTeXSlotV1';acquisition_timeout_ms=$AcquisitionTimeoutMs;master=$Master;engine=$Engine;started_utc=[DateTime]::UtcNow.ToString('o');passes=@();status='starting';abandoned_mutex=$false}
try {
 try {$owned=$mutex.WaitOne($AcquisitionTimeoutMs)} catch [Threading.AbandonedMutexException] {$owned=$true;$abandoned=$true}
 if (-not $owned) {$receipt.status='slot-unavailable';throw 'TeX slot unavailable within bounded timeout'}
 $receipt.abandoned_mutex=$abandoned
 Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class TamilTeXJob {
 [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)] public struct SI { public int cb; public string r;public string desktop;public string title;public int x,y,xs,ys,xc,yc,fill,flags;public short show,cb2;public IntPtr r2,stdin,stdout,stderr; }
 [StructLayout(LayoutKind.Sequential)] public struct PI { public IntPtr process,thread;public int pid,tid; }
 [StructLayout(LayoutKind.Sequential)] public struct ACCT {public long user,kernel,pu,pk;public uint faults,total,active,terminated;}
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool CreateProcess(string app,System.Text.StringBuilder cmd,IntPtr pa,IntPtr ta,bool inherit,uint flags,IntPtr env,string cwd,ref SI si,out PI pi);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode)] static extern IntPtr CreateJobObject(IntPtr a,string n);
 [DllImport("kernel32.dll")] static extern bool AssignProcessToJobObject(IntPtr j,IntPtr p);
 [DllImport("kernel32.dll")] static extern uint ResumeThread(IntPtr t);
 [DllImport("kernel32.dll")] static extern uint WaitForSingleObject(IntPtr h,uint ms);
 [DllImport("kernel32.dll")] static extern bool GetExitCodeProcess(IntPtr p,out uint code);
 [DllImport("kernel32.dll")] static extern bool QueryInformationJobObject(IntPtr j,int c,out ACCT a,int len,IntPtr ret);
 [DllImport("kernel32.dll")] static extern bool TerminateJobObject(IntPtr j,uint c);
 [DllImport("kernel32.dll")] static extern bool TerminateProcess(IntPtr p,uint c);
 [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
 public static uint Run(string exe,string args,string cwd) {
  IntPtr job=CreateJobObject(IntPtr.Zero,null); if(job==IntPtr.Zero)throw new Exception("CreateJobObject failed");
  PI pi=new PI();bool assigned=false;
  try {
   SI si=new SI();si.cb=Marshal.SizeOf(si);
   if(!CreateProcess(exe,new System.Text.StringBuilder("\""+exe+"\" "+args),IntPtr.Zero,IntPtr.Zero,false,0x08000004,IntPtr.Zero,cwd,ref si,out pi))throw new Exception("CreateProcess failed "+Marshal.GetLastWin32Error());
   if(!AssignProcessToJobObject(job,pi.process)){TerminateProcess(pi.process,1);throw new Exception("Job assignment failed");}
   assigned=true; ResumeThread(pi.thread);
   var deadline=DateTime.UtcNow.AddMinutes(6);
   while(true){ ACCT a;if(!QueryInformationJobObject(job,1,out a,Marshal.SizeOf(typeof(ACCT)),IntPtr.Zero))throw new Exception("Job query failed");if(a.active==0)break;if(DateTime.UtcNow>deadline)throw new Exception("Captured TeX tree timeout");System.Threading.Thread.Sleep(200); }
   uint result;GetExitCodeProcess(pi.process,out result);return result;
  } finally {
   if(assigned) {
    bool terminationRequested=false;
    while(true) {
     ACCT a;
     bool observed=QueryInformationJobObject(job,1,out a,Marshal.SizeOf(typeof(ACCT)),IntPtr.Zero);
     if(observed && a.active==0)break;
     if(!terminationRequested){TerminateJobObject(job,1);terminationRequested=true;}
     // Fail closed: never return to the mutex-release path until all captured processes are gone.
     System.Threading.Thread.Sleep(200);
    }
   } else if(pi.process!=IntPtr.Zero) {
    TerminateProcess(pi.process,1);
    WaitForSingleObject(pi.process,0xFFFFFFFF);
   }
   if(pi.thread!=IntPtr.Zero)CloseHandle(pi.thread);
   if(pi.process!=IntPtr.Zero)CloseHandle(pi.process);
   CloseHandle(job);
  }
 }
}
'@
 $enginePath=(Get-Command $Engine -ErrorAction Stop).Source
 for($pass=1;$pass -le $Passes;$pass++) {
  $code=[TamilTeXJob]::Run($enginePath,('-no-shell-escape -synctex=1 -interaction='+$Interaction+' -halt-on-error "'+$Master+'"'),$build)
  $log=Join-Path $build ([IO.Path]::GetFileNameWithoutExtension($Master)+'.log')
  $content=if(Test-Path -LiteralPath $log){Get-Content -Raw -LiteralPath $log}else{''}
  $issues=@($content -split "`n" | Where-Object {$_ -match '^!|Missing character:|Overfull|undefined references|LaTeX Warning'})
  $receipt.passes+=@{pass=$pass;exit_code=$code;issues=$issues}
  if($code -ne 0){$receipt.status='engine-failed';throw ('TeX engine failed with exit code '+$code)}
  if($BibTeX -and $pass -eq 1) {
   $bibPath=(Get-Command bibtex -ErrorAction Stop).Source
   $stem=[IO.Path]::GetFileNameWithoutExtension($Master)
   $bibCode=[TamilTeXJob]::Run($bibPath,('"'+$stem+'"'),$build)
   $bibLog=Join-Path $build ($stem+'.blg')
   $bibContent=if(Test-Path -LiteralPath $bibLog){Get-Content -Raw -LiteralPath $bibLog}else{''}
   $bibIssues=@($bibContent -split "\n" | Where-Object {$_ -match 'Warning--|error message|couldn.t open|not found|Illegal'})
   $receipt.bibliography=@{engine='bibtex';exit_code=$bibCode;issues=$bibIssues}
   if($bibCode -ne 0){$receipt.status='bibliography-failed';throw ('BibTeX failed with exit code '+$bibCode)}
  }
 }
 $receipt.status='built'
} catch { $receipt.error=$_.Exception.Message }
finally {
 if($owned){
  try { foreach($extension in @('log','fls','aux','out','blg','bbl')) {
   $f=Join-Path $build ([IO.Path]::GetFileNameWithoutExtension($Master)+'.'+$extension)
   if(Test-Path -LiteralPath $f){$s=Get-Content -Raw -LiteralPath $f;$s=$s.Replace($env:USERPROFILE,'<USERPROFILE>').Replace($env:USERPROFILE.Replace('\','/'),'<USERPROFILE>');[IO.File]::WriteAllText($f,$s,[Text.UTF8Encoding]::new($false))}
  }} finally {$mutex.ReleaseMutex()}
 }
 $mutex.Dispose()
 $receipt.finished_utc=[DateTime]::UtcNow.ToString('o')
 $json=($receipt|ConvertTo-Json -Depth 6).Replace($env:USERPROFILE,'<USERPROFILE>').Replace($env:USERPROFILE.Replace('\','/'),'<USERPROFILE>')
 $receiptPath=Join-Path $state ($ReceiptName+'.json')
 if(Test-Path -LiteralPath $receiptPath){Copy-Item -LiteralPath $receiptPath -Destination (Join-Path $state ($ReceiptName+'-'+[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')+'.json'))}
 $json|Set-Content -LiteralPath $receiptPath -Encoding utf8
 Write-Output $json
}
