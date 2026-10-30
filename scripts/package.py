#!/usr/bin/env python3
"""Create a deterministic allowlisted ZIP after source and metadata checks."""
import argparse
import hashlib
import json
import pathlib
import zipfile
from privacy_check import ROOT, check


def package(output, deny_terms=(), root=ROOT):
    root=pathlib.Path(root).resolve()
    files, problems=check(root,deny_terms)
    if problems:
        raise RuntimeError('Privacy check failed; run scripts/privacy_check.py for file-level reasons.')
    output=pathlib.Path(output).resolve()
    if root in output.parents and output.parent != root/'dist':
        raise RuntimeError('Inside the project, archives must be written to dist/.')
    output.parent.mkdir(parents=True,exist_ok=True)
    manifest=[]
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in files:
            name=path.relative_to(root).as_posix();data=path.read_bytes()
            item=zipfile.ZipInfo('claude/'+name,date_time=(2020,1,1,0,0,0))
            item.create_system=3
            item.compress_type=zipfile.ZIP_STORED if path.suffix in {'.mp4','.png','.jpg','.ico'} else zipfile.ZIP_DEFLATED
            item.external_attr=(0o100755 if path.suffix=='.sh' else 0o100644)<<16
            archive.writestr(item,data)
            manifest.append({'file':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    with zipfile.ZipFile(output) as archive:
        if archive.testzip():
            raise RuntimeError('Archive integrity check failed.')
        expected={'claude/'+item['file'] for item in manifest}
        if set(archive.namelist())!=expected:
            raise RuntimeError('Archive allowlist mismatch.')
    result={'passed':True,'archiveSha256':hashlib.sha256(output.read_bytes()).hexdigest(),'sourceFileCount':len(files),'files':manifest}
    output.with_suffix('.manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=pathlib.Path,default=ROOT/'dist/claude-source.zip')
    parser.add_argument('--deny-term',action='append',default=[])
    args=parser.parse_args();report=package(args.output,args.deny_term)
    print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
