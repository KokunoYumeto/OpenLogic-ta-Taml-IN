param(
  [Parameter(Mandatory=$true)][string]$Master,
  [Parameter(Mandatory=$true)][string]$ReaderSlug,
  [ValidateSet('tex4ht','lua4ht')][string]$Backend='tex4ht',
  [ValidateRange(1000,60000)][int]$AcquisitionTimeoutMs=60000,
  [ValidateRange(1,20)][int]$ProcessTimeoutMinutes=12,
  [string]$StateDirectory='C:\interlanguage-task-state\openlogic-ta-Taml-IN'
)

$ErrorActionPreference='Stop'
$build=[IO.Path]::GetFullPath($PSScriptRoot)
$repo=[IO.Path]::GetFullPath((Join-Path $build '..'))
$state=[IO.Path]::GetFullPath($StateDirectory)
if(-not (Test-Path -LiteralPath $state -PathType Container)){throw 'State directory does not exist'}
if($Master -notmatch '^[a-zA-Z0-9_-]+\.tex$'){throw 'Unsafe master filename'}
if($ReaderSlug -notmatch '^[a-z0-9][a-z0-9-]+$'){throw 'Unsafe reader slug'}
$masterPath=Join-Path $build $Master
if(-not (Test-Path -LiteralPath $masterPath -PathType Leaf)){throw 'Master file does not exist'}

$workRoot=[IO.Path]::GetFullPath((Join-Path $repo 'epub\work'))
$readerRoot=[IO.Path]::GetFullPath((Join-Path $workRoot $ReaderSlug))
if(-not $readerRoot.StartsWith($workRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){
  throw 'Resolved reader work directory escaped the EPUB work root'
}
$htmlDir=Join-Path $readerRoot 'html'
$auxDir=Join-Path $readerRoot 'aux'
if(Test-Path -LiteralPath $readerRoot){Remove-Item -LiteralPath $readerRoot -Recurse -Force}
New-Item -ItemType Directory -Path $htmlDir,$auxDir -Force | Out-Null

# open-logic-tokenize makes ! active in the preamble.  The installed TeX4ht
# configuration parses a literal ! while \Preamble is initialized, so restore
# the ordinary catcode just for that initialization and reactivate it before
# translated content is read.  The generated adapter is build material; the
# authoritative reader master remains untouched.
$masterText=[IO.File]::ReadAllText($masterPath,[Text.UTF8Encoding]::new($false))
$pdfMath='\input{../translation/tamil-pdf-math.sty}'
if($masterText.IndexOf($pdfMath,[StringComparison]::Ordinal) -ge 0){
  $masterText=$masterText.Replace($pdfMath,'% EPUB uses native MathML; PDF ActualText wrappers are intentionally omitted.')
}
$begin='\begin{document}'
$beginIndex=$masterText.IndexOf($begin,[StringComparison]::Ordinal)
if($beginIndex -lt 0){throw 'Master has no begin-document marker'}
$compat="\ifdefined\HCode`n  \catcode 33=12\relax`n  \AtBeginDocument{\catcode 33=13\relax}`n\fi`n"
$adapted=$masterText.Substring(0,$beginIndex)+$compat+$masterText.Substring($beginIndex)
$adaptedMaster=Join-Path $auxDir ($ReaderSlug+'-epub-master.tex')
[IO.File]::WriteAllText($adaptedMaster,$adapted,[Text.UTF8Encoding]::new($false))

$mutex=New-Object Threading.Mutex($false,'Global\InterlanguageTeXSlotV1')
$owned=$false
$abandoned=$false
$receipt=[ordered]@{
  schema='openlogic-tamil-epub-html-guard/1'
  mutex='Global\InterlanguageTeXSlotV1'
  acquisition_timeout_ms=$AcquisitionTimeoutMs
  process_timeout_minutes=$ProcessTimeoutMinutes
  master=$Master
  master_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $masterPath).Hash.ToLowerInvariant()
  adapter_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $adaptedMaster).Hash.ToLowerInvariant()
  reader_slug=$ReaderSlug
  converter='make4ht'
  converter_version=''
  backend=$Backend
  options=@('lualatex','html5','mathml','charset=utf-8','fn-in','no-shell-escape')
  started_utc=[DateTime]::UtcNow.ToString('o')
  status='starting'
  abandoned_mutex=$false
  exit_code=$null
  issues=@()
  output_files=@()
}

try {
  if($Backend -eq 'lua4ht'){
    $lua4htStyle=(& kpsewhich lua4ht.sty 2>$null | Out-String).Trim()
    if(-not $lua4htStyle){$receipt.status='backend-unavailable';throw 'lua4ht backend requested but lua4ht.sty is unavailable'}
  }
  try {$owned=$mutex.WaitOne($AcquisitionTimeoutMs)}
  catch [Threading.AbandonedMutexException] {$owned=$true;$abandoned=$true}
  if(-not $owned){$receipt.status='slot-unavailable';throw 'TeX slot unavailable within bounded timeout'}
  $receipt.abandoned_mutex=$abandoned

  Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class TamilEpubTeXJob {
 [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)] public struct SI { public int cb; public string r; public string desktop; public string title; public int x,y,xs,ys,xc,yc,fill,flags; public short show,cb2; public IntPtr r2,stdin,stdout,stderr; }
 [StructLayout(LayoutKind.Sequential)] public struct PI { public IntPtr process,thread; public int pid,tid; }
 [StructLayout(LayoutKind.Sequential)] public struct ACCT { public long user,kernel,pu,pk; public uint faults,total,active,terminated; }
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
 public static uint Run(string exe,string args,string cwd,int timeoutMinutes) {
  IntPtr job=CreateJobObject(IntPtr.Zero,null); if(job==IntPtr.Zero)throw new Exception("CreateJobObject failed");
  PI pi=new PI(); bool assigned=false;
  try {
   SI si=new SI(); si.cb=Marshal.SizeOf(si);
   if(!CreateProcess(exe,new System.Text.StringBuilder("\""+exe+"\" "+args),IntPtr.Zero,IntPtr.Zero,false,0x08000004,IntPtr.Zero,cwd,ref si,out pi))throw new Exception("CreateProcess failed "+Marshal.GetLastWin32Error());
   if(!AssignProcessToJobObject(job,pi.process)){TerminateProcess(pi.process,1);throw new Exception("Job assignment failed");}
   assigned=true; ResumeThread(pi.thread);
   var deadline=DateTime.UtcNow.AddMinutes(timeoutMinutes);
   while(true){
    ACCT a;
    if(!QueryInformationJobObject(job,1,out a,Marshal.SizeOf(typeof(ACCT)),IntPtr.Zero))throw new Exception("Job query failed");
    if(a.active==0)break;
    if(DateTime.UtcNow>deadline)throw new Exception("Captured TeX tree timeout");
    System.Threading.Thread.Sleep(200);
   }
   uint result; GetExitCodeProcess(pi.process,out result); return result;
  } finally {
   if(assigned) {
    bool terminationRequested=false;
    while(true) {
     ACCT a;
     bool observed=QueryInformationJobObject(job,1,out a,Marshal.SizeOf(typeof(ACCT)),IntPtr.Zero);
     if(observed && a.active==0)break;
     if(!terminationRequested){TerminateJobObject(job,1);terminationRequested=true;}
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

  $make4ht=(Get-Command make4ht -ErrorAction Stop).Source
  $version=(& $make4ht --version 2>&1 | Out-String).Trim()
  $receipt.converter_version=$version
  $htmlArg=$htmlDir.Replace('\','/')
  $auxArg=$auxDir.Replace('\','/')
  $adaptedMasterArg=$adaptedMaster.Replace('\','/')
  $args=(
    '-a warning -l -b "'+$Backend+'" -f html5 -d "'+$htmlArg+'" -B "'+$auxArg+'" '+
    '-j "'+$ReaderSlug+'" "'+$adaptedMasterArg+'" '+
    '"mathml,charset=utf-8,fn-in" "" "" "-no-shell-escape -interaction=batchmode -halt-on-error"'
  )
  $oldEpoch=$env:SOURCE_DATE_EPOCH
  $env:SOURCE_DATE_EPOCH='1788532058'
  try {$code=[TamilEpubTeXJob]::Run($make4ht,$args,$build,$ProcessTimeoutMinutes)}
  finally {$env:SOURCE_DATE_EPOCH=$oldEpoch}
  $receipt.exit_code=$code

  $logs=@(Get-ChildItem -LiteralPath $readerRoot -Recurse -File -ErrorAction SilentlyContinue | Where-Object {$_.Extension -in @('.log','.lg')})
  $issuePattern='^!|Missing character:|undefined references|LaTeX Warning|TeX capacity exceeded|Emergency stop|Fatal error'
  foreach($log in $logs){
    $content=Get-Content -Raw -LiteralPath $log.FullName
    foreach($line in ($content -split "`n" | Where-Object {$_ -match $issuePattern})){
      $receipt.issues+=@{file=$log.Name;line=$line.Trim()}
    }
  }
  $outputs=@(Get-ChildItem -LiteralPath $htmlDir -Recurse -File -ErrorAction SilentlyContinue | Sort-Object FullName)
  foreach($file in $outputs){
    $relative=[IO.Path]::GetRelativePath($readerRoot,$file.FullName).Replace('\','/')
    $receipt.output_files+=@{path=$relative;bytes=$file.Length;sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()}
  }
  if($code -ne 0){$receipt.status='converter-failed';throw ('make4ht failed with exit code '+$code)}
  $xhtml=@($outputs | Where-Object {$_.Extension -in @('.html','.xhtml')})
  if($xhtml.Count -eq 0){$receipt.status='no-html-output';throw 'make4ht produced no HTML/XHTML output'}
  $receipt.status='generated'
} catch {
  $errorMessage=$_.Exception.Message
  if($receipt.status -eq 'starting'){
    if($errorMessage -like '*Captured TeX tree timeout*'){$receipt.status='converter-timeout'}
    else{$receipt.status='converter-exception'}
  }
  $receipt.error=$errorMessage
} finally {
  if($owned){$mutex.ReleaseMutex()}
  $mutex.Dispose()
  $receipt.finished_utc=[DateTime]::UtcNow.ToString('o')
  $json=($receipt|ConvertTo-Json -Depth 8).Replace($env:USERPROFILE,'<USERPROFILE>').Replace($env:USERPROFILE.Replace('\','/'),'<USERPROFILE>')
  $receiptPath=Join-Path $state ('EPUB-HTML-'+$ReaderSlug.ToUpperInvariant().Replace('-','_')+'-RECEIPT.json')
  if(Test-Path -LiteralPath $receiptPath){
    Copy-Item -LiteralPath $receiptPath -Destination (Join-Path $state ([IO.Path]::GetFileNameWithoutExtension($receiptPath)+'-'+[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')+'.json'))
  }
  [IO.File]::WriteAllText($receiptPath,$json,[Text.UTF8Encoding]::new($false))
  Write-Output $json
}
