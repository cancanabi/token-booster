import itertools,json,os,random,subprocess,sys,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'scripts'))
from token_booster.context import (safe_file,collect,read_safe,outline,candidates,exact_budget_choice,plan,Candidate)
from token_booster.usage import summarize,compare
from token_booster.compress import compress_for_hook,critical_lines,protects_all_summaries
from post_tool_use import rewrite
from compact import compact

class ContextTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name).resolve()
  (self.root/'auth.py').write_text('class Login:\n    def sign_in(self):\n        return True\n',encoding='utf-8')
  (self.root/'report.md').write_text('# Summary\n## Authentication\n',encoding='utf-8')
  (self.root/'other.py').write_text('def calculate_sum(a,b):\n    return a+b\n',encoding='utf-8')
 def test_safe_file(self):self.assertTrue(safe_file(self.root,self.root/'auth.py'))
 def test_sensitive_names(self):
  for n in ('.env','.env.production','creds.secret.json','client-private-key.txt','credentials.yml','id_rsa','secret_notes.py'):
   (self.root/n).write_text('secret')
   self.assertFalse(safe_file(self.root,self.root/n),n)
 def test_reject_outside(self):self.assertFalse(safe_file(self.root,self.root/'..'/'outside.py'))
 def test_reject_symlinks(self):
  (self.root/'alias.py').symlink_to(self.root/'auth.py')
  self.assertFalse(safe_file(self.root,self.root/'alias.py'))
  self.assertIsNone(read_safe(self.root,self.root/'alias.py'))
 def test_reject_symlink_directory(self):
  (self.root/'link').symlink_to(self.root,target_is_directory=True)
  self.assertFalse(safe_file(self.root,self.root/'link'/'auth.py'))
 def test_reject_binary(self):
  (self.root/'nul.py').write_bytes(b'123\x00abc')
  self.assertIsNone(read_safe(self.root,self.root/'nul.py'))
 def test_reject_invalid_utf8(self):
  (self.root/'bad.py').write_bytes(b'\xff\xfe')
  self.assertIsNone(read_safe(self.root,self.root/'bad.py'))
 def test_reject_large(self):
  (self.root/'large.py').write_bytes(b'x'*128001)
  self.assertIsNone(read_safe(self.root,self.root/'large.py'))
 def test_skip_dirs(self):
  (self.root/'node_modules').mkdir();(self.root/'node_modules'/'auth.js').write_text('token');
  self.assertTrue(all('node_modules' not in str(x) for x in collect(self.root)))
 def test_python_outline(self):
  got=outline(self.root/'auth.py',(self.root/'auth.py').read_text())
  self.assertIn('Login',got);self.assertIn('Login.sign_in',got);self.assertNotIn('return True',got)
 def test_markdown_outline(self):
  got=outline(self.root/'report.md',(self.root/'report.md').read_text());self.assertIn('Authentication',got)
 def test_json_outline(self):
  got=outline(Path('config.json'),'{'+'"beta":1,"alpha":2'+'}')
  self.assertIn('alpha',got);self.assertNotIn('"beta":1',got)
 def test_js_outline(self):self.assertIn('fetchData',outline(Path('app.js'),'function fetchData() {}'))
 def test_rank_auth(self):
  results=candidates(self.root,'login authentication')
  self.assertTrue(any(x.path=='auth.py' for x in results))
 def test_rank_deterministic(self):
  self.assertEqual(candidates(self.root,'login'),candidates(self.root,'login'))
 def test_no_relevant(self):self.assertEqual(candidates(self.root,'nonexistentunique'),[])
 def test_plan_respects_budget(self):
  x=plan(self.root,'login authentication',budget=400)
  self.assertLessEqual(x['total_outline_bytes'],160)
 def test_plan_tiny_rejected(self):
  with self.assertRaises(ValueError):plan(self.root,'login',1)
 def test_outline_invalid_code(self):self.assertIn('No supported',outline(Path('bad.py'),'def ('))
 def test_cli_rank(self):
  p=subprocess.run([sys.executable,str(ROOT/'scripts/tb.py'),'rank','login','--root',str(self.root)],text=True,capture_output=True)
  self.assertEqual(p.returncode,0,p.stderr);self.assertIn('auth.py',p.stdout)
 def test_cli_map_no_secrets(self):
  (self.root/'.env').write_text('MY_SECRET')
  p=subprocess.run([sys.executable,str(ROOT/'scripts/tb.py'),'map',str(self.root)],capture_output=True,text=True)
  self.assertEqual(p.returncode,0);self.assertNotIn('.env',p.stdout)
 def test_cli_outline_blocked(self):
  p=subprocess.run([sys.executable,str(ROOT/'scripts/tb.py'),'outline','.env','--root',str(self.root)],capture_output=True,text=True)
  self.assertEqual(p.returncode,2)

class OptimizationTests(unittest.TestCase):
 @staticmethod
 def item(idx,cost,utility):return Candidate(f'p{idx}','',cost,utility,0.)
 def test_exact_counterexample_to_greedy(self):
  # Greedy by score/byte picks 0 (8/4), but 1+2 wins (10/6).
  items=[self.item(0,4,8),self.item(1,3,5),self.item(2,3,5)]
  self.assertEqual(sum(i.utility for i in exact_budget_choice(items,6)),10)
 def test_exact_against_bruteforce_random(self):
  rng=random.Random(1337)
  for _ in range(120):
   items=[self.item(i,rng.randrange(1,20),rng.randrange(1,80)) for i in range(9)]
   budget=rng.randrange(0,80)
   actual=sum(i.utility for i in exact_budget_choice(items,budget))
   expected=max(sum(items[i].utility for i in range(9) if mask>>i&1) for mask in range(1<<9) if sum(items[i].bytes for i in range(9) if mask>>i&1)<=budget)
   self.assertEqual(actual,expected)
 def test_tie_smallest_bytes(self):
  items=[self.item(0,4,10),self.item(1,3,10)]
  self.assertEqual([x.path for x in exact_budget_choice(items,4)],['p1'])
 def test_zero_budget(self):self.assertEqual(exact_budget_choice([self.item(0,4,10)],0),[])
 def test_oversized_budget(self):
  with self.assertRaises(ValueError):exact_budget_choice([],100001)
 def test_too_many_items(self):
  with self.assertRaises(ValueError):exact_budget_choice([self.item(i,1,1) for i in range(25)],100)
 def test_summary_preserved(self):
  text='\n'.join('processing '+str(i) for i in range(600))+'\n1200 tests passed\n'
  rew=compress_for_hook(text,lambda s:compact(s,max_lines=65,context=0))
  self.assertIsNotNone(rew);self.assertIn('1200 tests passed',rew)
 def test_summary_loss_pass_through(self):
  text='\n'.join('processing '+str(i) for i in range(600))+'\n900 tests passed\n'
  self.assertIsNone(compress_for_hook(text,lambda s:'INCOMPLETE shortened'))
 def test_summary_lines(self):
  self.assertEqual(critical_lines('hello\nRan 7 tests in 0.03s\n'),['Ran 7 tests in 0.03s'])
 def test_truncated_summary_rejected(self):
  text='\n'.join('processing '+str(i) for i in range(600))+'\n1200 tests passed '+'x'*400+'\n'
  self.assertIsNone(compress_for_hook(text,lambda s:compact(s,max_lines=65,max_chars=220,context=0)))
 def test_control_bytes_unchanged(self):
  e={'hook_event_name':'PostToolUse','tool_name':'Bash','tool_input':{'command':'npm test'},'tool_response':{'stdout':'abc\x00'*1500,'stderr':'','isImage':False,'interrupted':False}}
  self.assertIsNone(rewrite(e))

class TranscriptTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def transcript(self,lines):
  p=self.root/'usage.jsonl';p.write_text('\n'.join(json.dumps(l) if isinstance(l,dict) else str(l) for l in lines)+'\n',encoding='utf8');return p
 def test_unique_messages(self):
  p=self.transcript([{'message':{'id':'x','usage':{'input_tokens':4,'output_tokens':2}}},{'message':{'id':'y','usage':{'input_tokens':10,'output_tokens':9}}}])
  self.assertEqual(summarize(p)['summed_reported_tokens'],25)
 def test_duplicate_id_last(self):
  p=self.transcript([{'message':{'id':'a','usage':{'input_tokens':20}}},{'message':{'id':'a','usage':{'input_tokens':30}}}])
  self.assertEqual(summarize(p)['tokens_reported']['input_tokens'],30)
 def test_anonymous(self):
  p=self.transcript([{'message':{'usage':{'output_tokens':4}}}])
  self.assertEqual(summarize(p)['anonymous_usage_entries'],1)
 def test_no_prompt_leak(self):
  p=self.transcript([{'message':{'id':'a','content':'TOP_SECRET','usage':{'output_tokens':4}}}])
  self.assertNotIn('TOP_SECRET',json.dumps(summarize(p)))
 def test_invalid_lines(self):
  p=self.transcript(['oops','null',{'message':{'usage':{'input_tokens':2}}}])
  self.assertEqual(summarize(p)['tokens_reported']['input_tokens'],2)
 def test_reject_negative_and_boolean(self):
  p=self.transcript([{'message':{'usage':{'input_tokens':-5,'output_tokens':True}}}])
  self.assertEqual(summarize(p)['summed_reported_tokens'],0)
 def test_symlink_denied(self):
  p=self.transcript([{'message':{'usage':{'input_tokens':2}}}]);alias=self.root/'alias';alias.symlink_to(p)
  with self.assertRaises(ValueError):summarize(alias)
 def test_compare(self):
  a={'tokens_reported':{k:100 for k in ('input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens')}}
  b={'tokens_reported':{k:80 for k in a['tokens_reported']}}
  self.assertEqual(compare(a,b)['usage_comparison']['input_tokens']['change_pct'],-20.)
 def test_cli_usage(self):
  p=self.transcript([{'message':{'id':'a','usage':{'input_tokens':7}}}])
  r=subprocess.run([sys.executable,str(ROOT/'scripts/tb.py'),'usage',str(p)],text=True,capture_output=True)
  self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['tokens_reported']['input_tokens'],7)

if __name__=='__main__':unittest.main()
