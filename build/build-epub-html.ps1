param(
  [Parameter(Mandatory=$true)][string]$Master,
  [Parameter(Mandatory=$true)][string]$ReaderSlug,
  [ValidateSet('tex4ht','lua4ht')][string]$Backend='tex4ht',
  [ValidateSet('lualatex','xelatex')][string]$Engine='lualatex',
  [ValidateRange(1000,60000)][int]$AcquisitionTimeoutMs=60000,
  [ValidateRange(1,60)][int]$ProcessTimeoutMinutes=12,
  [switch]$ImportExternalLabels,
  [switch]$ResumeMissingGlyph,
  [string]$StateDirectory=$PSScriptRoot
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
if($ResumeMissingGlyph){
  if($Master -ne 'tamil-complete.tex' -or $ReaderSlug -ne 'complete-main'){
    throw 'Missing-glyph resume applies only to the complete main EPUB'
  }
  if(-not (Test-Path -LiteralPath (Join-Path $auxDir 'complete-main.idv') -PathType Leaf)){
    throw 'Missing-glyph resume requires the preserved complete-main IDV'
  }
} elseif(Test-Path -LiteralPath $readerRoot){
  Remove-Item -LiteralPath $readerRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $htmlDir,$auxDir -Force | Out-Null

# open-logic-tokenize makes ! active in the preamble.  The installed TeX4ht
# configuration parses a literal ! while \Preamble is initialized, so restore
# the ordinary catcode just for that initialization and reactivate it before
# translated content is read.  The generated adapter is build material; the
# authoritative reader master remains untouched.
$masterText=[IO.File]::ReadAllText($masterPath,[Text.UTF8Encoding]::new($false))
# The installed 2023 TeX4ht loops on an ordinary math array when newer LaTeX
# leaves \partokencontext enabled. TeX4ht upstream now clears it itself; set
# the same primitive before \documentclass in this generated adapter only.
$masterText="\ifdefined\partokencontext\partokencontext=0\relax\fi`n"+$masterText
$logicStyle='\input{\olpath/sty/open-logic.sty}'
if($masterText.IndexOf($logicStyle,[StringComparison]::Ordinal) -lt 0){throw 'Master does not load the expected OpenLogic style'}
# The installed bussproofs.4ht leaves an open paragraph after \DisplayProof;
# ending a prooftree immediately then fails at \end{center}. Close the
# paragraph in the generated EPUB preamble while retaining every proof tree.
$proofEnd='\renewcommand\endprooftree{\DisplayProof\par\proofSkipAmount\end{center}}'
$masterText=$masterText.Replace($logicStyle,$logicStyle+"`n"+$proofEnd)
# In display math, TeX4ht's proof-image hook needs an explicit paragraph
# before the closing math delimiter. Apply this after TeX4ht has patched
# \DisplayProof, and only for calls entered from math mode.
$proofMath='\AtBeginDocument{\let\TASavedDisplayProof\DisplayProof\renewcommand\DisplayProof{\ifmmode\TASavedDisplayProof\par\else\TASavedDisplayProof\fi}}'
$masterText=$masterText.Replace($logicStyle+"`n"+$proofEnd,$logicStyle+"`n"+$proofEnd+"`n"+$proofMath)
# Give TeX4ht a bounded, literal proof-image alternative. Its default
# source-derived alt stream embeds MathML markup into an HTML attribute and
# corrupts neighboring content for complex labelled proof trees.
$proofAlt='\AtBeginDocument{\Configure{DisplayProof}{\Picture*[Proof tree diagram]{}}{\EndPicture}}'
$masterText=$masterText.Replace($logicStyle+"`n"+$proofEnd+"`n"+$proofMath,$logicStyle+"`n"+$proofEnd+"`n"+$proofMath+"`n"+$proofAlt)
$sourceOverrides=@()
if($Master -eq 'tamil-complete.tex' -and $ReaderSlug -eq 'complete-main'){
  # This installed TeX4ht fails on otherwise valid unbraced scripts whose
  # base is a one-argument macro. Braces preserve the same math atom and are
  # inserted only in generated EPUB inputs, never the frozen translation.
  $scriptRegex=[regex]::new('([_^])\\([A-Za-z]+)\{([^{}]*)\}')
  $sourceFiles=@(Get-ChildItem -LiteralPath (Join-Path $repo 'translation\content') -Recurse -File -Filter '*.tex' | Sort-Object FullName)
  $basenameCounts=@{}
  foreach($file in $sourceFiles){
    if(-not $basenameCounts.ContainsKey($file.BaseName)){$basenameCounts[$file.BaseName]=0}
    $basenameCounts[$file.BaseName]++
  }
  $overrideDir=Join-Path $readerRoot 'overrides'
  New-Item -ItemType Directory -Path $overrideDir -Force | Out-Null
  $overrideArguments=@{}
  $totalScriptRepairs=0
  foreach($file in $sourceFiles){
    $sourcePath=$file.FullName
    $sourceText=[IO.File]::ReadAllText($sourcePath,[Text.UTF8Encoding]::new($false))
    $occurrences=$scriptRegex.Matches($sourceText).Count
    $isProofAlign=$file.BaseName -eq 'interpretation-rules'
    if($occurrences -eq 0 -and -not $isProofAlign){continue}
    if($basenameCounts[$file.BaseName] -ne 1){throw ('Non-unique EPUB override basename: '+$file.BaseName)}
    $repaired=$scriptRegex.Replace($sourceText,[Text.RegularExpressions.MatchEvaluator]{
      param($match)
      $match.Groups[1].Value+'{'+$match.Value.Substring(1)+'}'
    })
    if($scriptRegex.IsMatch($repaired)){throw ('Unbraced script remains after EPUB repair: '+$file.FullName)}
    $additionalRepairs=0
    if($file.BaseName -eq 'frame-completeness'){
      # A final align* row also breaks this TeX4ht on the single-symbol
      # superscript R^\Sigma; the same chapter otherwise converts unchanged.
      $old='R^\Sigma \Delta_1\Delta_2.'
      if(([regex]::Matches($repaired,[regex]::Escape($old))).Count -ne 1){
        throw 'Expected exactly one final-row modal-frame EPUB repair'
      }
      $repaired=$repaired.Replace($old,'R^{\Sigma} \Delta_1\Delta_2.')
      $additionalRepairs=1
    }
    if($isProofAlign){
      # bussproofs' two in-math proof trees fail in TeX4ht. Render the same
      # trees as separate centered proof images in the EPUB only.
      $blocks=[regex]::Matches($repaired,'(?s)\\begin\{align\*\}.*?\\end\{align\*\}')
      if($blocks.Count -ne 1){throw 'Expected one proof-rule alignment in the EPUB source'}
      $block=$blocks[0].Value
      if(([regex]::Matches($block,[regex]::Escape('\DisplayProof'))).Count -ne 2 -or
         ([regex]::Matches($block,'(?m)^[ \t]*&[ \t]*\r?$')).Count -ne 1 -or
         ([regex]::Matches($block,'(?m)^[ \t]*\\\\[ \t]*\r?$')).Count -ne 1){
        throw 'Proof-rule alignment shape changed; EPUB adapter requires review'
      }
      $centered=$block.Replace('\begin{align*}','\begin{center}').Replace('\end{align*}','\end{center}')
      $centered=[regex]::Replace($centered,'(?m)^[ \t]*&[ \t]*\r?\n','')
      $centered=[regex]::Replace($centered,'(?m)^[ \t]*\\\\[ \t]*\r?\n',"\par`r`n")
      if(([regex]::Matches($centered,[regex]::Escape('& \Axiom'))).Count -ne 1){throw 'Second EPUB proof-row marker changed'}
      $centered=$centered.Replace('& \Axiom','\Axiom')
      $repaired=$repaired.Replace($block,$centered)
      # This section imports one sibling after the rule display. Its
      # subfile path must still resolve from the temporary overlay directory.
      $childImport='\subfile{rules-G2c}'
      if(([regex]::Matches($repaired,[regex]::Escape($childImport))).Count -ne 1){
        throw 'Expected one nested rules-G2c import in the EPUB override'
      }
      $childPath=Join-Path (Split-Path -Parent $sourcePath) 'rules-G2c.tex'
      if(-not (Test-Path -LiteralPath $childPath -PathType Leaf)){throw 'Nested rules-G2c source is missing'}
      $childArgument=[IO.Path]::GetRelativePath($overrideDir,$childPath).Replace('\','/')
      if([IO.Path]::GetFullPath((Join-Path $overrideDir $childArgument)) -ne $childPath){
        throw 'Nested rules-G2c EPUB import does not resolve to its original source'
      }
      $repaired=$repaired.Replace($childImport,'\subfile{'+$childArgument+'}')
      $additionalRepairs=2
    }
    $overridePath=Join-Path $overrideDir $file.Name
    [IO.File]::WriteAllText($overridePath,$repaired,[Text.UTF8Encoding]::new($false))
    # subfiles/import prepends the active source directory even to an
    # absolute argument, so resolve against the original source location.
    $argument=[IO.Path]::GetRelativePath((Split-Path -Parent $sourcePath),$overridePath).Replace('\','/')
    if([IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $sourcePath) $argument)) -ne $overridePath){
      throw ('EPUB override path does not resolve: '+$file.FullName)
    }
    $overrideArguments[$file.BaseName]=$argument
    $totalScriptRepairs+=$occurrences
    $sourceOverrides+=@{
      name=$file.BaseName
      source=[IO.Path]::GetRelativePath($repo,$sourcePath).Replace('\','/')
      source_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath).Hash.ToLowerInvariant()
      override_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $overridePath).Hash.ToLowerInvariant()
      subfile_argument=$argument
      replacement_count=($occurrences+$additionalRepairs)
    }
  }
  if($sourceOverrides.Count -ne 12 -or $totalScriptRepairs -ne 65){
    throw ('Expected 65 unbraced macro scripts plus one proof alignment across 12 EPUB-only overlays, found '+$totalScriptRepairs+' / '+$sourceOverrides.Count)
  }
  $overrideTeX='\NewDocumentCommand\TAEpubSubfile{m}{'
  foreach($override in $sourceOverrides){
    $name=$override.name
    $overrideTeX+='\ifstrequal{#1}{'+$name+'}{\typeout{TA-EPUB-OVERRIDE: '+$name+'}\TAEpubOriginalSubfile{'+$overrideArguments[$name]+'}}{'
  }
  $overrideTeX+='\TAEpubOriginalSubfile{#1}'+('}'*$sourceOverrides.Count)+'}'
  $overrideTeX+="`n"+'\AtBeginDocument{\let\TAEpubOriginalSubfile\subfile\let\subfile\TAEpubSubfile}'
  $masterText=$masterText.Replace($logicStyle+"`n"+$proofEnd+"`n"+$proofMath+"`n"+$proofAlt,$logicStyle+"`n"+$proofEnd+"`n"+$proofMath+"`n"+$proofAlt+"`n"+$overrideTeX)
}
$pdfMath='\input{../translation/tamil-pdf-math.sty}'
if($masterText.IndexOf($pdfMath,[StringComparison]::Ordinal) -ge 0){
  $masterText=$masterText.Replace($pdfMath,'% EPUB uses native MathML; PDF ActualText wrappers are intentionally omitted.')
}
$pdfExternal='\externaldocument{tamil-complete}[tamil-complete.pdf]'
$labelInput=''
if($masterText.IndexOf($pdfExternal,[StringComparison]::Ordinal) -ge 0){
  # Import only label records from the validated main PDF AUX. This retains
  # section/theorem numbers without TeX4ht's cross-document PDF-link parser.
  $mainAux=Join-Path $build 'tamil-complete.aux'
  if(-not (Test-Path -LiteralPath $mainAux -PathType Leaf)){throw 'Main-volume AUX is required for companion references'}
  # These are the 19 distinct cross-volume destinations observed in the
  # validated companion PDF. Import each ordinary and cleveref label only;
  # loading every main-volume label also duplicates local names and makes
  # TeX4ht's label writer pathological.
  $externalKeys=@(
    'pl:syn:sem:prop:semanticalfacts',
    'fol:seq:ptn:prop:incons',
    'fol:seq:prv:prop:provability-contr',
    'fol:seq:prv:prop:provability-exhaustive',
    'fol:seq:ppr:prop:provability-land-left',
    'fol:seq:ppr:prop:provability-land-right',
    'fol:seq:ppr:prop:provability-lor',
    'fol:seq:ppr:prop:provability-lif-left',
    'fol:seq:ppr:prop:provability-lif-right',
    'fol:ntd:prv:prop:provability-contr',
    'fol:ntd:prv:prop:provability-exhaustive',
    'fol:ntd:ppr:prop:provability-land-left',
    'fol:ntd:ppr:prop:provability-land-right',
    'fol:ntd:ppr:prop:provability-lor',
    'fol:ntd:ppr:prop:provability-lif-left',
    'fol:ntd:ppr:prop:provability-lif-right',
    'mod:bas:iso:thm:isom',
    'mod:bas:dlo:thm:cantorQ',
    'pt:seq:inv:prop:G3c-cont-adm'
  )
  $wanted=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
  foreach($key in $externalKeys){[void]$wanted.Add($key);[void]$wanted.Add($key+'@cref')}
  $labels=@(Get-Content -LiteralPath $mainAux -Encoding UTF8 | Where-Object {
    $_ -match '^\\newlabel\{([^}]+)\}' -and $wanted.Contains($Matches[1])
  })
  if($labels.Count -ne $wanted.Count){throw "Main-volume AUX does not contain all 38 cross-volume labels: $($labels.Count)"}
  $definitions=@('% Read-only main-volume label values; no cross-EPUB PDF hyperlink targets.')
  foreach($line in $labels){
    if($line -notmatch '^\\newlabel\{([^}]+)\}(\{.*\})$'){throw 'Malformed selected main-volume label record'}
    $key=$Matches[1]
    $value=$Matches[2]
    $body=$value.Substring(1,$value.Length-2)
    $definitions+='\expandafter\gdef\csname r@'+$key+'\endcsname{'+$body+'}'
  }
  $labelFile=Join-Path $auxDir 'main-volume-labels.tex'
  [IO.File]::WriteAllLines($labelFile,[string[]]$definitions,[Text.UTF8Encoding]::new($false))
  if($ImportExternalLabels){$labelInput='\input{../epub/work/'+$ReaderSlug+'/aux/main-volume-labels.tex}'}
  $masterText=$masterText.Replace($pdfExternal,'% Main-volume reference numbers are imported before begin-document.')
}
$pdfOpen='\href{tamil-complete.pdf}{முதன்மை வாசிப்பு நூலைத் திறக்க}'
if($masterText.IndexOf($pdfOpen,[StringComparison]::Ordinal) -ge 0){
  $masterText=$masterText.Replace($pdfOpen,'முதன்மை EPUB வாசிப்பு நூல் தனியாக வழங்கப்படுகிறது')
}
$pdfReferenceClaim='பிற மேற்கோள்கள் முதன்மை நூலுக்கும் செல்கின்றன.'
if($masterText.IndexOf($pdfReferenceClaim,[StringComparison]::Ordinal) -ge 0){
  $masterText=$masterText.Replace($pdfReferenceClaim,'பிற மேற்கோள்கள் முதன்மை நூலின் இடங்களைச் சுட்டுகின்றன.')
}
$begin='\begin{document}'
$beginIndex=$masterText.IndexOf($begin,[StringComparison]::Ordinal)
if($beginIndex -lt 0){throw 'Master has no begin-document marker'}
$compat="\ifdefined\HCode`n  \catcode 33=12\relax`n  \AtBeginDocument{\catcode 33=13\relax}`n\fi`n"
$adapted=$masterText.Substring(0,$beginIndex)+$compat
if($labelInput){$adapted+=$labelInput+"`n"}
$adapted+=$masterText.Substring($beginIndex)
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
  source_overrides=$sourceOverrides
  reader_slug=$ReaderSlug
  import_external_labels=[bool]$ImportExternalLabels
  resume_missing_glyph=[bool]$ResumeMissingGlyph
  converter='make4ht'
  converter_version=''
  backend=$Backend
  engine=$Engine
  options=@($Engine,'html5','mathml','charset=utf-8','fn-in','no-shell-escape','partokencontext=0','prooftree-paragraph-close','math-proof-paragraph-close','proof-image-alt','source-script-epub-overrides')
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
  $engineFlag=if($Engine -eq 'xelatex'){'-x'}else{'-l'}
  $args=(
    '-a warning '+$engineFlag+' -b "'+$Backend+'" -f html5 -d "'+$htmlArg+'" -B "'+$auxArg+'" '+
    '-j "'+$ReaderSlug+'" "'+$adaptedMasterArg+'" '+
    '"mathml,charset=utf-8,fn-in" "" "" "-no-shell-escape -interaction=batchmode -halt-on-error"'
  )
  if($ResumeMissingGlyph){
    $previousPath=Join-Path $state 'EPUB-HTML-COMPLETE_MAIN-RECEIPT.json'
    $previous=Get-Content -LiteralPath $previousPath -Raw | ConvertFrom-Json
    if($previous.status -notin @('converter-failed','converter-exception') -or $previous.exit_code -ne 1 -or
       $previous.master_sha256 -ne $receipt.master_sha256 -or
       $previous.adapter_sha256 -ne $receipt.adapter_sha256){
      throw 'Preserved main conversion does not match this exact EPUB adapter'
    }
    $code=1
  } else {
    $oldEpoch=$env:SOURCE_DATE_EPOCH
    $env:SOURCE_DATE_EPOCH='1788532058'
    try {$code=[TamilEpubTeXJob]::Run($make4ht,$args,$build,$ProcessTimeoutMinutes)}
    finally {$env:SOURCE_DATE_EPOCH=$oldEpoch}
  }
  $receipt.exit_code=$code
  $effectiveCode=$code

  # TeX4ht's 2023 St Mary map requests a bitmap for the exact
  # \leftrightarroweq glyph but the bitmap generator fails on this machine.
  # All other requested assets must already exist. Render its IDV page to
  # an outline SVG inside the same mutex/job guard and retain a truthful
  # record of make4ht's original exit code.
  if($code -eq 1 -and $Master -eq 'tamil-complete.tex' -and $ReaderSlug -eq 'complete-main'){
    $logPath=Join-Path $auxDir 'complete-main.log'
    $lgPath=Join-Path $auxDir 'complete-main.lg'
    $htmlPath=Join-Path $auxDir 'complete-main.html'
    $cssPath=Join-Path $auxDir 'complete-main.css'
    if((Test-Path -LiteralPath $logPath -PathType Leaf) -and
       (Test-Path -LiteralPath $lgPath -PathType Leaf) -and
       (Test-Path -LiteralPath $htmlPath -PathType Leaf) -and
       (Test-Path -LiteralPath $cssPath -PathType Leaf)){
      $fatalLines=@(Get-Content -LiteralPath $logPath | Where-Object {$_ -match '^!|^Emergency stop|^Fatal error'})
      $needs=@()
      foreach($line in Get-Content -LiteralPath $lgPath){
        if($line -match '^--- needs --- complete-main\.idv\[(\d+)\] ==> (\S+) ---$'){
          $needs+=@{page=[int]$Matches[1];name=$Matches[2]}
        }
      }
      $missing=@($needs | Where-Object {-not (Test-Path -LiteralPath (Join-Path $auxDir $_.name) -PathType Leaf)})
      $htmlText=[IO.File]::ReadAllText($htmlPath,[Text.UTF8Encoding]::new($false))
      $glyphReference='src="stmary10-2d.png" alt="???"'
      $glyphCount=([regex]::Matches($htmlText,[regex]::Escape($glyphReference))).Count
      if($fatalLines.Count -eq 0 -and $needs.Count -eq 954 -and $missing.Count -eq 1 -and
         $missing[0].page -eq 1336 -and $missing[0].name -ceq 'stmary10-2d.png' -and
         $glyphCount -eq 2 -and $htmlText.TrimEnd().EndsWith('</html>')){
        $glyphSvg=Join-Path $auxDir 'stmary10-2d.svg'
        $dvisvgm=(Get-Command dvisvgm -ErrorAction Stop).Source
        $glyphArgs='-n -p 1336 --exact -c 1.4,1.4 -o "stmary10-2d.svg" "complete-main.idv"'
        $glyphCode=[TamilEpubTeXJob]::Run($dvisvgm,$glyphArgs,$auxDir,3)
        if($glyphCode -ne 0 -or -not (Test-Path -LiteralPath $glyphSvg -PathType Leaf)){
          $receipt.asset_recovery=@{status='failed';dvisvgm_exit_code=$glyphCode;svg_exists=(Test-Path -LiteralPath $glyphSvg -PathType Leaf)}
          throw 'Guarded St Mary glyph vector recovery failed'
        }
        $svgText=[IO.File]::ReadAllText($glyphSvg,[Text.UTF8Encoding]::new($false))
        if($svgText.IndexOf('<svg',[StringComparison]::Ordinal) -lt 0){throw 'Recovered St Mary glyph is not SVG'}
        $htmlText=$htmlText.Replace($glyphReference,'src="stmary10-2d.svg" alt="left-right arrow equality"')
        [IO.File]::WriteAllText($htmlPath,$htmlText,[Text.UTF8Encoding]::new($false))
        $effectiveCode=0
        $receipt.asset_recovery=@{
          status='pass'
          reason='TeX4ht St Mary bitmap generator failed for leftrightarroweq'
          requested_assets=$needs.Count
          missing_before=1
          glyph_references_replaced=$glyphCount
          idv_page=1336
          idv_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $auxDir 'complete-main.idv')).Hash.ToLowerInvariant()
          svg_bytes=(Get-Item -LiteralPath $glyphSvg).Length
          svg_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $glyphSvg).Hash.ToLowerInvariant()
          dvisvgm_exit_code=$glyphCode
        }
      }
    }
  }
  $receipt.effective_exit_code=$effectiveCode

  # On Windows, make4ht can leave final HTML/CSS beside its -B auxiliary
  # files even when -d names a separate output directory. Collect only
  # rendered publication assets from that directory before auditing output.
  if($effectiveCode -eq 0){
    $assetExtensions=@('.html','.xhtml','.htm','.css','.svg','.png','.jpg','.jpeg','.gif','.webp','.woff','.woff2','.otf','.ttf')
    $rendered=@(Get-ChildItem -LiteralPath $auxDir -Recurse -File -ErrorAction SilentlyContinue | Where-Object {$_.Extension.ToLowerInvariant() -in $assetExtensions})
    foreach($file in $rendered){
      $relative=[IO.Path]::GetRelativePath($auxDir,$file.FullName)
      $destination=Join-Path $htmlDir $relative
      $destinationDirectory=Split-Path -Parent $destination
      New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
      Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
    }
  }

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
  if($effectiveCode -ne 0){$receipt.status='converter-failed';throw ('make4ht failed with exit code '+$code)}
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
