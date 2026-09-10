"""Check declared resource dependencies, not scholarly merit or publication likelihood."""
import math


def positive_number(value, field):
    if type(value) not in (int,float) or not math.isfinite(value) or value<=0:
        raise ValueError(field+' must be a finite positive number')


def text(value, field):
    if not isinstance(value,str) or not value.strip():raise ValueError(field+' needs text')


def strings(value, field):
    if not isinstance(value,list):raise ValueError(field+' must be a list')
    for item in value:text(item,field)


def assess_plan(plan):
    if not isinstance(plan,dict) or plan.get('schema_version')!=1:
        raise ValueError('Unsupported research plan schema')
    if plan.get('source_nature') not in {'synthetic','user_reported','mixed','unknown'}:
        raise ValueError('Research plan needs source_nature')
    constraints=plan['constraints']
    positive_number(constraints['months_available'],'months_available')
    strings(constraints['prohibited_methods'],'prohibited_methods')
    resources={}
    if not isinstance(plan['resources'],list) or not isinstance(plan['routes'],list):
        raise ValueError('Resources and routes must be lists')
    for resource in plan['resources']:
        for key in ['id','description','source']:text(resource.get(key),key)
        if resource['id'] in resources:raise ValueError('Duplicate resource ID')
        if resource.get('availability') not in {'available','planned','uncertain','unavailable'}:
            raise ValueError('Invalid resource availability')
        if resource.get('permission') not in {'confirmed','pending','denied','not_required'}:
            raise ValueError('Invalid resource permission')
        resources[resource['id']]=resource
    results=[];seen=set()
    for route in plan['routes']:
        for key in ['id','question','claim_scope','minimum_evidence','fallback']:text(route.get(key),key)
        if route['id'] in seen:raise ValueError('Duplicate route ID')
        seen.add(route['id'])
        strings(route['methods'],'methods');strings(route['requires'],'requires')
        positive_number(route['estimated_months'],'estimated_months')
        blockers=[];pending=[]
        for method in sorted(set(route['methods']) & set(constraints['prohibited_methods'])):
            blockers.append({'type':'prohibited_method','method':method})
        if route['estimated_months']>constraints['months_available']:
            blockers.append({'type':'time_exceeds_declared_budget'})
        for resource_id in route['requires']:
            if resource_id not in resources:raise ValueError('Unknown resource: '+resource_id)
            resource=resources[resource_id]
            if resource['availability']=='unavailable' or resource['permission']=='denied':
                blockers.append({'type':'resource_unavailable','resource':resource_id})
            elif resource['availability']!='available' or resource['permission']=='pending':
                pending.append({'type':'resource_pending','resource':resource_id,
                                'availability':resource['availability'],'permission':resource['permission']})
        results.append({'route_id':route['id'],
                        'resource_status':'blocked' if blockers else 'conditional' if pending else 'ready_for_planning',
                        'blockers':blockers,'pending':pending})
    return {'source_nature':plan['source_nature'],'routes':results,
            'scope':'Declared resource feasibility only; synthetic resources are not real access. No assessment of evidence sufficiency, novelty, causal identification or acceptance.'}
