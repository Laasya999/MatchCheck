import pandas as pd
import gradio as gr
from datetime import datetime
from copy import deepcopy
import tempfile, os, json
from uuid import uuid4

# TABLE 1: CLIENTS

clients = pd.DataFrame([
    {
        "client_id": "C001",
        "name": "Ananya",
        "age": 29,
        "city": "Bengaluru",
        "service": "Partner Search"
    },
    {
        "client_id": "C002",
        "name": "Meera",
        "age": 32,
        "city": "Mumbai",
        "service": "Partner Search"
    },
    {
        "client_id": "C003",
        "name": "Vikram",
        "age": 34,
        "city": "Hyderabad",
        "service": "Partner Search"
    }
])




# TABLE 2: CLIENT PREFERENCES

from datetime import timedelta

today = datetime.now().date()

preferences = pd.DataFrame([
    # Ananya's preferences
    ["C001", "smoking", "No", "Strict", "Client-confirmed", 10],
    ["C001", "children", "Yes", "Strict", "Client-confirmed", 15],
    ["C001", "city", "Bengaluru", "Flexible", "Client-confirmed", 75],
    ["C001", "settlement", "India", "Strict", "Client-confirmed", 20],
    ["C001", "age", "29-34", "Flexible", "Client-confirmed", 15],
    ["C001", "intent", "Marriage", "Strict", "Client-confirmed", 10],

    # Meera's preferences
    ["C002", "smoking", "No", "Flexible", "Matchmaker-recorded", 25],
    ["C002", "children", "No", "Strict", "Client-confirmed", 10],
    ["C002", "city", "Mumbai", "Strict", "Client-confirmed", 90],
    ["C002", "settlement", "India", "Flexible", "Client-confirmed", 30],
    ["C002", "age", "31-38", "Flexible", "Client-confirmed", 20],
    ["C002", "intent", "Marriage", "Strict", "Client-confirmed", 10],

    # Vikram's preferences
    ["C003", "smoking", "No", "Strict", "Client-confirmed", 5],
    ["C003", "children", "Yes", "Flexible", "Matchmaker-recorded", 20],
    ["C003", "city", "Hyderabad", "Flexible", "Client-confirmed", 70],
    ["C003", "settlement", "India", "Strict", "Client-confirmed", 15],
    ["C003", "age", "28-35", "Flexible", "Client-confirmed", 10],
    ["C003", "intent", "Marriage", "Strict", "Client-confirmed", 5]
], columns=[
    "client_id",
    "attribute",
    "desired_value",
    "preference_type",
    "source",
    "days_since_confirmation"
])

# Calculate the confirmation date
preferences["last_confirmed_date"] = preferences[
    "days_since_confirmation"
].apply(lambda days: today - timedelta(days=days))

# Flag preferences due for review
REVIEW_THRESHOLD = 60

preferences["review_due"] = (
    preferences["days_since_confirmation"] > REVIEW_THRESHOLD
)




# TABLE 3: CANDIDATE PROFILES

candidates = pd.DataFrame([
    ["P001", "Arjun", 32, "Man", "Bengaluru",
     "No", "Yes", "India", "Marriage",
     "Internal network", "Verified"],

    ["P002", "Rahul", 31, "Man", "Bengaluru",
     "Yes", "Yes", "India", "Marriage",
     "External platform", "Self-reported"],

    ["P003", "Aditya", 33, "Man", "Hyderabad",
     "No", "Yes", "India", "Marriage",
     "Internal network", "Verified"],

    ["P004", "Karan", 30, "Man", "Bengaluru",
     None, "Yes", "India", "Marriage",
     "External platform", "Incomplete"],

    ["P005", "Rohan", 35, "Man", "Mumbai",
     "No", "No", "Abroad", "Marriage",
     "External platform", "Self-reported"],

    ["P006", "Siddharth", 34, "Man", "Mumbai",
     "No", "No", "India", "Marriage",
     "Internal network", "Verified"],

    ["P007", "Nisha", 30, "Woman", "Hyderabad",
     "No", "Yes", "India", "Marriage",
     "Internal network", "Verified"],

    ["P008", "Priya", 33, "Woman", "Bengaluru",
     "No", "No", "India", "Marriage",
     "Referral", "Self-reported"],

    ["P009", "Kavya", 29, "Woman", "Hyderabad",
     "No", "Yes", "India", None,
     "External platform", "Incomplete"],

    ["P010", "Varun", 36, "Man", "Mumbai",
     "Yes", "No", "India", "Marriage",
     "Referral", "Self-reported"]

], columns=[
    "candidate_id",
    "name",
    "age",
    "gender",
    "city",
    "smoking",
    "children",
    "settlement",
    "intent",
    "profile_source",
    "verification_status"
])





# TABLE 4: HISTORICAL FEEDBACK

feedback = pd.DataFrame([
    [
        "F001", "C001", "P005", "Rejected",
        "I would prefer someone based in Bengaluru. "
        "Mumbai might be difficult for me.",
        "city", 45
    ],
    [
        "F002", "C001", "P003", "Accepted",
        "Hyderabad could work if the person is "
        "open to relocating in the future.",
        "city", 20
    ],
    [
        "F003", "C001", "P002", "Rejected",
        "Smoking is a deal-breaker for me.",
        "smoking", 12
    ],
    [
        "F004", "C002", "P001", "Rejected",
        "Our plans regarding children do not align.",
        "children", 25
    ],
    [
        "F005", "C002", "P010", "Accepted",
        "I prefer non-smokers, but I am open "
        "to speaking with him.",
        "smoking", 15
    ],
    [
        "F006", "C003", "P008", "Rejected",
        "I would prefer someone in Hyderabad "
        "because relocation may be difficult.",
        "city", 18
    ]

], columns=[
    "feedback_id",
    "client_id",
    "candidate_id",
    "outcome",
    "feedback_text",
    "related_attribute",
    "days_ago"
])

# Calculate feedback dates
feedback["feedback_date"] = feedback["days_ago"].apply(
    lambda days: today - timedelta(days=days)
)

# Identify how feedback was classified
feedback["classification_source"] = "Manually tagged"

# Feedback does not automatically change preferences
feedback["preference_update_confirmed"] = False



# Check that all referenced clients and candidates exist



# Add the recorded candidate gender preference

clients["seeking_gender"] = clients["client_id"].map({
    "C001": "Man",
    "C002": "Man",
    "C003": "Woman"
})





# DECISION ENGINE - PART 1
# Compare an individual preference

def evaluate_preference(attribute, desired_value,
                        actual_value, preference_type):

    # Rule 1: Handle missing information
    if pd.isna(actual_value) or str(actual_value).strip().lower() in ("", "unknown", "n/a", "none"):
        return "Missing information"

    # Rule 2: Handle age ranges
    if attribute == "age":
        min_age, max_age = map(
            int, desired_value.split("-")
        )

        actual_age = int(actual_value)

        is_aligned = min_age <= actual_age <= max_age

    # Rule 3: Compare other attributes
    else:
        is_aligned = (
            str(desired_value).strip().lower()
            ==
            str(actual_value).strip().lower()
        )

    # Rule 4: Classify the result
    if is_aligned:
        return "Aligned"

    elif preference_type == "Strict":
        return "Strict conflict"

    else:
        return "Flexible mismatch"



READY='Ready for review'; POT='Potential candidate'; CLAR='Requires clarification'; EX='Excluded'
CATS=[READY,POT,CLAR,EX]
candidates['availability']='Available'
candidates.loc[candidates.candidate_id=='P010','availability']='Unknown'
feedback.loc[feedback.feedback_id=='F002','outcome']='Conditional'
def fresh():
    return dict(p=preferences.copy(deep=True), c=candidates.copy(deep=True), log=[], changes=[], exceptions={})
def evaluate(s,cid,pid):
    c=s['c'].set_index('candidate_id').loc[pid]; client=clients.set_index('client_id').loc[cid]
    if c.gender!=client.seeking_gender: raise ValueError('Ineligible profile')
    rows=[]; blocks=[]; clar=[]; warnings=[]; flexible=[]
    if c.availability not in ['Available','Unknown']: blocks.append('availability')
    if c.availability=='Unknown': clar.append('availability')
    for _,p in s['p'][s['p'].client_id==cid].iterrows():
        a=p.attribute; v=c[a]; stale=(datetime.now().date()-p.last_confirmed_date).days>60
        status=evaluate_preference(a,p.desired_value,v,p.preference_type)
        strict=p.preference_type=='Strict'; confirmed=p.source=='Client-confirmed'
        exception=s['exceptions'].get((cid,pid,a))
        if stale or not confirmed: warnings.append(f'{a}: reconfirm recorded preference ({p.source}).')
        if status=='Strict conflict':
            if stale or not confirmed: clar.append(a)
            elif exception and exception['desired']==p.desired_value and exception['actual']==str(v): flexible.append(a); status='Client-approved exception'
            else: blocks.append(a)
        elif status=='Missing information': (clar if strict else flexible).append(a)
        elif status=='Flexible mismatch': flexible.append(a)
        rows.append([a,p.desired_value,'Unknown' if pd.isna(v) else v,p.preference_type,status,p.source,str(p.last_confirmed_date),stale])
    if c.verification_status!='Verified': warnings.append('Profile is not fully verified; independently confirm important data.')
    cat=EX if blocks else CLAR if clar else POT if flexible else READY
    return cat,rows,blocks,clar,warnings,flexible
COLS=['Preference','Expected','Actual','Priority','Assessment','Source','Date','Review due']
def pool(s,cid):
    gender=clients.set_index('client_id').loc[cid,'seeking_gender']; return s['c'][(s['c'].gender==gender)]
def shortlist(s,cid,filter):
    out=[]
    for _,c in pool(s,cid).iterrows():
        cat,r,b,q,w,f=evaluate(s,cid,c.candidate_id)
        prev=any(x['client']==cid and x['candidate']==c.candidate_id for x in s['log']) or not feedback[(feedback.client_id==cid)&(feedback.candidate_id==c.candidate_id)].empty
        out.append([c.candidate_id,c['name'],c.age,c.city,cat,len(f),sum(x[4]=='Missing information' for x in r),c.verification_status,prev,', '.join(b+q+f) or 'No known blockers'])
    df=pd.DataFrame(out,columns=['ID','Candidate','Age','Location','Category','Context issues','Unknowns','Verification','Previously reviewed','Reason'])
    if len(df): df=df.sort_values(['Category','Context issues','Unknowns','ID'],key=lambda x:x.map({v:i for i,v in enumerate(CATS)}) if x.name=='Category' else x)
    summary=' | '.join(f'**{x}:** {sum(df.Category==x)}' for x in CATS)
    view=df if filter=='All profiles' else df[df.Category!=EX] if filter=='Active review queue' else df[df.Category==filter]
    opts=[(f'{r.Candidate} ({r.ID})',r.ID) for _,r in view.iterrows()]
    return summary,view,gr.Dropdown(choices=opts,value=None)
def brief(s,cid,pid):
    if not pid: return 'Select a candidate.',pd.DataFrame(columns=COLS),'',None
    cat,r,b,q,w,f=evaluate(s,cid,pid); c=s['c'].set_index('candidate_id').loc[pid]
    h=feedback[(feedback.client_id==cid)&((feedback.candidate_id==pid)|feedback.related_attribute.isin(b+q+f+[x[0] for x in r if x[-1]]))]
    txt=f'### {c["name"]} · {cat}\n\n**Blockers:** {", ".join(b+q) or "None"}\n\n'+'\n'.join('- '+x for x in w)
    hist='### Historical feedback\n'+('\n'.join(f'- {x.outcome}: {x.feedback_text}' for _,x in h.iterrows()) or 'No relevant feedback.')
    return txt,pd.DataFrame(r,columns=COLS),hist,(cid,pid)
def act(s,cid,pid,reviewed,kind,field,value,evidence):
    if not pid or reviewed!=(cid,pid): return s,'Review the selected pair first.'
    if not evidence.strip(): return s,'Enter confirmation evidence or decision rationale.'
    s=deepcopy(s); cat,r,b,q,w,f=evaluate(s,cid,pid); now=datetime.now().isoformat(timespec='seconds')
    if kind in ['Update candidate','Reconfirm preference','Client-approved exception']:
        row=next((x for x in r if x[0]==field),None)
        if kind=='Update candidate':
            valid={'smoking':['Yes','No'],'children':['Yes','No'],'intent':['Marriage','Other'],'settlement':['India','Abroad'],'availability':['Available','Unknown','Paused','Matched','Unavailable']}
            if field not in valid or value not in valid[field]: return s,'Choose a supported field and valid value (see instructions).'
            mask=s['c'].candidate_id==pid; old=str(s['c'].loc[mask,field].iloc[0]); s['c'].loc[mask,field]=value
        elif kind=='Reconfirm preference':
            if row is None: return s,'Select a preference field.'
            mask=(s['p'].client_id==cid)&(s['p'].attribute==field); old=str(s['p'].loc[mask,'last_confirmed_date'].iloc[0]); s['p'].loc[mask,'last_confirmed_date']=datetime.now().date(); s['p'].loc[mask,'source']='Client-confirmed'; value='Confirmed unchanged'
        else:
            if field not in b or row is None or row[4]!='Strict conflict': return s,'Exception requires a current confirmed strict conflict.'
            old='No exception'; value='Client-approved exception'; s['exceptions'][(cid,pid,field)]={'desired':row[1],'actual':str(row[2]),'evidence':evidence}
        s['changes'].append(dict(time=now,client=cid,candidate=pid,action=kind,field=field,old=old,new=value,evidence=evidence))
    else:
        if kind=='Proceed' and cat in [EX,CLAR]: return s,'Resolve strict conflicts, missing information or reconfirmation blockers first.'
        record=dict(time=now,client=cid,candidate=pid,recommendation=cat,decision=kind,reason=evidence,rule_version='3',snapshot=json.dumps(r,default=str),exceptions=json.dumps([v for k,v in s['exceptions'].items() if k[:2]==(cid,pid)]))
        if s['log'] and all(s['log'][-1].get(k)==v for k,v in record.items() if k!='time'): return s,'Duplicate decision not recorded.'
        s['log'].append(record)
    return s,'Saved. Assessment refreshed.'
def export(s):
    f=tempfile.NamedTemporaryFile(suffix='.csv',delete=False); f.close(); pd.DataFrame([dict(record_type='Decision',**x) for x in s['log']]+[dict(record_type='Change',**x) for x in s['changes']]).to_csv(f.name,index=False); return f.name

from html import escape
CSS = '\n.gradio-container {background:#f3eadc !important; color:#29251f !important; max-width:1450px !important; margin:auto !important; padding:24px !important; font-family:Arial,sans-serif !important; color-scheme:light;}\n#masthead {padding:14px 4px 24px; border-bottom:1px solid #dfd2c0; margin-bottom:20px;}\n.brand {display:flex;align-items:center;gap:12px;font-family:Georgia,serif;font-weight:bold;font-size:19px;}.brandmark {background:#a8732e;color:white;border-radius:50%;width:38px;height:38px;display:grid;place-items:center;font-weight:normal;}\n.eyebrow {font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#786b58;font-weight:bold;}.hero-title {font-family:Georgia,serif;font-size:42px;line-height:1.1;margin:18px 0 8px;color:#29251f;}.hero-title em {color:#a8732e;font-weight:normal;}.subtle {color:#73695d;font-size:14px;line-height:1.6;}\n.panel {background:#fffdf9 !important;border:1px solid #e6dbcc !important;border-radius:20px !important;padding:22px !important;box-shadow:0 7px 20px #503b1610 !important;gap:14px !important;}\n.panel h2,.panel h3 {font-family:Georgia,serif !important;color:#29251f !important;font-weight:normal !important;} .panel h2 {font-size:25px !important;}\n.kpis {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:8px 0 16px;}.kpi {padding:14px;border-radius:14px;background:#f5eee2;border:1px solid #e8dfd1;}.kpi strong {display:block;font:32px Georgia,serif;margin-bottom:7px;}.kpi span {font-size:12px;font-weight:bold;}.ready {background:#e3efe6;color:#356a58;}.potential {background:#f9edcf;color:#886321;}.clarify {background:#eee8d9;color:#786029;}.excluded {background:#f5dfda;color:#a24f42;}\n.profile-list {display:grid;gap:9px;}.profile {display:flex;align-items:center;gap:12px;padding:13px 10px;border-bottom:1px solid #e9dfd2;}.avatar {width:42px;height:42px;flex-shrink:0;border-radius:13px;background:#eee1ca;display:grid;place-items:center;font:20px Georgia,serif;color:#906326;}.profile-name {font:20px Georgia,serif;color:#29251f;}.profile-info {font-size:12px;color:#756c60;margin-top:4px;}.badge {display:inline-block;padding:6px 10px;border-radius:30px;font-size:11px;font-weight:bold;}.profile .badge {margin-left:auto;}.section-tag {display:inline-block;background:#e3efe6;color:#356a58;padding:5px 9px;border-radius:6px;font-size:11px;font-weight:bold;letter-spacing:1px;}.detail-title {font:30px Georgia,serif;margin:12px 0;}.detail-line {font-size:14px;margin:8px 0;line-height:1.5;}.warning {background:#f9edcf;padding:10px;border-radius:9px;margin:8px 0;color:#78591d;font-size:13px;}.footnote {font-size:12px;color:#756c60;margin-top:15px;}\nbutton.primary {background:#777f29 !important;border-color:#777f29 !important;color:white !important;border-radius:12px !important;min-height:44px;} button.secondary {border-radius:12px !important;} textarea,input {border-radius:9px !important;} footer {display:none !important;}\n@media(max-width:700px){.gradio-container{padding:12px !important;}.hero-title{font-size:32px;}.kpis{grid-template-columns:repeat(2,1fr);}.panel{padding:14px !important;}.profile{flex-wrap:wrap;}.profile .badge{margin-left:0;}}\n'
CSS += """
.client-card {background:#f5eee2;border-radius:14px;padding:14px;} .client-card .detail-title {margin:0 0 5px;} .pref-line {font-size:13px;margin-top:6px;color:#29251f;} .pref-line small {color:#786b58;} #candidate-picker label {border:1px solid #e6dbcc!important;border-radius:12px!important;padding:14px!important;background:#fffdf9!important;min-height:54px;cursor:pointer;} #candidate-picker label:has(input:checked) {background:#f3eadc!important;border-color:#a8732e!important;} #candidate-picker .wrap {flex-direction:column!important;align-items:stretch!important;} #category-filter label {border-radius:10px!important;}
"""

def build():
    theme=gr.themes.Soft(primary_hue=gr.themes.colors.olive if hasattr(gr.themes.colors,'olive') else gr.themes.colors.green, neutral_hue=gr.themes.colors.stone).set(body_background_fill="#f3eadc",body_background_fill_dark="#f3eadc",body_text_color="#29251f",body_text_color_dark="#29251f",block_background_fill="#fffdf9",block_background_fill_dark="#fffdf9",input_background_fill="#fffdf9",input_background_fill_dark="#fffdf9",button_primary_background_fill="#777f29",button_primary_text_color="#ffffff")
    styles={READY:'ready',POT:'potential',CLAR:'clarify',EX:'excluded'}
    def cards(s,c,f):
        _,df,drop=shortlist(s,c,f)
        _,all_df,_=shortlist(s,c,'All profiles')
        kpis='<div class="kpis">'+''.join(f'<div class="kpi {styles[k]}"><strong>{sum(all_df.Category==k)}</strong><span>{k}</span></div>' for k in CATS)+'</div>'
        items=[]
        for _,r in df.iterrows():
            items.append(f'<div class="profile"><div class="avatar">{escape(r.Candidate[0])}</div><div><div class="profile-name">{escape(r.Candidate)} <small>· {r.Age}</small></div><div class="profile-info">{escape(r.Location)} · {escape(r.ID)}'+(' · Previously reviewed' if r["Previously reviewed"] else '')+f'</div><div class="profile-info">{escape(r.Reason)}</div></div><span class="badge {styles[r.Category]}">{escape(r.Category)}</span></div>')
        return '<div class="subtle">'+str(len(df))+' of '+str(len(all_df))+' profiles visible</div>'+kpis,df,gr.Radio(choices=[(f'{r.Candidate} · {r.Age} · {r.Location} | {r.Category} — {r.Reason}',r.ID) for _,r in df.iterrows()],value=None)
    def detail(s,c,p):
        _,table,history,review=brief(s,c,p)
        if not p: return '<div class="subtle">Choose a candidate from the shortlist to see their decision brief.</div>',table,history,review
        cat,rows,blocks,clar,warnings,flex=evaluate(s,c,p)
        person=s['c'].set_index('candidate_id').loc[p]
        html=f'<span class="section-tag">PREFERENCE CHECK</span><div class="detail-title">{escape(person["name"])} · {person.age}</div><span class="badge {styles[cat]}">{cat}</span><div class="detail-line">{escape(person.city)} · {escape(person.verification_status)} · {escape(person.availability)}</div>'
        if blocks or clar: html+='<div class="warning">Attention: '+escape(', '.join(blocks+clar))+'</div>'
        html+=''.join('<div class="warning">'+escape(w)+'</div>' for w in warnings)
        return html,table,history,review
    with gr.Blocks(title='MatchCheck | Matchmaker studio') as demo:
        demo._matchcheck_theme=theme
        state=gr.State(fresh()); reviewed=gr.State(None)
        gr.HTML('<div id="masthead"><div class="brand"><span class="brandmark">tdc</span> The Date Crew · MatchCheck <span class="eyebrow" style="margin-left:auto">Assessment prototype</span></div><div class="hero-title">Better introductions, <em>thoughtfully.</em></div><div class="subtle">A matchmaker workspace for checking known preferences before introductions.</div></div>')
        with gr.Tabs():
            with gr.Tab('Matchmaker workspace'):
                with gr.Row():
                    with gr.Column(scale=5,elem_classes=['panel']):
                        gr.Markdown('## Your shortlist')
                        cid=gr.Dropdown([(f"{r['name']} · {r.city}",r.client_id) for _,r in clients.iterrows()],value='C001',label='Select client')
                        filt=gr.Radio(['All profiles','Active review queue']+CATS,value='All profiles',label='Filter candidates',elem_id='category-filter')
                        refresh=gr.Button('Refresh shortlist',variant='primary')
                        client_info=gr.HTML()
                        summary=gr.HTML()
                        pid=gr.Radio([],label='Select any candidate to open their decision brief',elem_id='candidate-picker')
                        with gr.Accordion('Detailed shortlist table',open=False): table=gr.Dataframe(interactive=False,wrap=True)
                    with gr.Column(scale=7,elem_classes=['panel']):
                        gr.Markdown('## Decision brief')
                        btxt=gr.HTML(); bt=gr.Dataframe(interactive=False,wrap=True); hist=gr.Markdown()
                        gr.Markdown('## Next action')
                        kind=gr.Dropdown(['Proceed','Clarify','Defer','Do not share','Update candidate','Reconfirm preference','Client-approved exception'],value='Clarify',label='Action')
                        field=gr.Dropdown(['smoking','children','intent','settlement','city','age','availability'],label='Field (for changes only)')
                        val=gr.Textbox(label='New candidate value',info='Yes / No; Marriage / Other; India / Abroad; availability: Available, Unknown, Paused, Matched, Unavailable.')
                        ev=gr.Textbox(label='Rationale / explicit confirmation evidence',lines=2)
                        save=gr.Button('Save and re-evaluate',variant='primary'); msg=gr.Markdown()
            with gr.Tab('Decision history'):
                with gr.Column(elem_classes=['panel']):
                    gr.Markdown('## Recorded decisions'); logs=gr.Dataframe(interactive=False)
                    gr.Markdown('## Changes and confirmations'); changes=gr.Dataframe(interactive=False)
                    download=gr.Button('Export CSV',variant='primary'); file=gr.File()
            with gr.Tab('About'):
                gr.Markdown('## About MatchCheck\nScreens an existing candidate pool against recorded preferences. Human review remains necessary. No reciprocal matching, external sourcing or live LLM. All records are fictional; session changes reset. The 60-day review threshold is illustrative.')
        gr.HTML('<div class="footnote">Synthetic data only · Session-local demo · One-sided preference screening, not a compatibility prediction.</div>')
        def client_summary(s,c):
            person=clients.set_index('client_id').loc[c]
            prefs=s['p'][s['p'].client_id==c]
            return f'<div class="client-card"><div class="detail-title">{escape(person["name"])}</div><div class="subtle">{person.age} · {escape(person.city)} · {escape(person.service)}</div>'+''.join(f'<div class="pref-line">{escape(str(r.attribute).title())}: <b>{escape(str(r.desired_value))}</b> <small>({escape(str(r.preference_type))})</small></div>' for _,r in prefs.iterrows())+'</div>'
        def reset(s,c,f): return (client_summary(s,c),*cards(s,c,f),*detail(s,c,None),'','')
        outs=[client_info,summary,table,pid,btxt,bt,hist,reviewed,ev,msg]
        for e in [cid.input,filt.input,refresh.click,demo.load]: e(reset,[state,cid,filt],outs)
        def choose(s,c,p): return (*detail(s,c,p),"","")
        pid.input(choose,[state,cid,pid],[btxt,bt,hist,reviewed,ev,msg])
        def save_all(s,c,p,r,k,field,value,evidence,f):
            s,msg=act(s,c,p,r,k,field,value,evidence); su,ta,drop=cards(s,c,f)
            opts=[(f'{row.Candidate} · {row.Age} · {row.Location} | {row.Category} — {row.Reason}',row.ID) for _,row in ta.iterrows()]
            selected=p if p in [x[1] for x in opts] else None
            return s,msg,client_summary(s,c),su,ta,gr.Radio(choices=opts,value=selected),*detail(s,c,selected),pd.DataFrame(s['log']),pd.DataFrame(s['changes']),' '
        save.click(save_all,[state,cid,pid,reviewed,kind,field,val,ev,filt],[state,msg,client_info,summary,table,pid,btxt,bt,hist,reviewed,logs,changes,ev])
        download.click(export,state,file)
    return demo
if __name__=='__main__':
    demo=build()
    demo.launch(theme=demo._matchcheck_theme,css=CSS)
