#!/usr/bin/env python3
"""Initialize an episode state/card without replacing any existing user material."""
import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

STAGES = ('design','slides','script','script_review','demo','avatar','compose','review','covers','publish','archive')
SERIES = '29天带你玩转Vibe Coding'


def locate_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / 'AI学习' / '内容' / '定稿').is_dir():
            return parent
    raise ValueError('Cannot locate workspace. Pass --root explicitly.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, help='Existing workspace root; defaults to skill-linked workspace')
    parser.add_argument('--day', type=int, required=True, choices=range(13,30))
    parser.add_argument('--title', default=None)
    args = parser.parse_args()
    root = (args.root or locate_root()).expanduser().resolve()
    if not root.is_dir():
        parser.error(f'Workspace root does not exist: {root}')
    base = root / 'AI学习' / '内容' / '定稿'
    day_dir = base / f'Day{args.day}'
    state_path = day_dir / f'Day{args.day}_制作状态.json'
    card_path = day_dir / f'Day{args.day}_任务卡.md'
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding='utf-8'))
        if state.get('day') != args.day:
            raise ValueError('Existing state belongs to a different episode; nothing overwritten.')
        print(json.dumps({'result':'existing_state_preserved','state':str(state_path),'current_stage':state.get('current_stage')}, ensure_ascii=False))
        return
    title = args.title or ('刷新丢数据？保存之后再留份备份' if args.day == 14 else None)
    previous = base / f'Day{args.day - 1}'
    state = {
        'schema_version':1,
        'day':args.day,
        'series':SERIES,
        'title':title,
        'updated_at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds'),
        'current_stage':'design',
        'stage_status':{stage:'not_started' for stage in STAGES},
        'baseline':{
            'source_day':args.day - 1,
            'source_directory':str(previous),
            'source_exists':previous.is_dir(),
            'verified':False,
            'notes':'Day13终点无保存功能；本期需实测起点。' if args.day == 14 else None,
        },
        'design_review':{'text_ready':False,'visual_ready':False,'user_reviewed':False,'approved_version':None},
        'script_review':{'provider':'Gemini','status':'not_started','selected_mode':None,'raw_review':None,'adoption_report':None,'revised_script':None},
        'layout':json.loads((Path(__file__).resolve().parent.parent / 'assets/landscape-layout.json').read_text(encoding='utf-8')),
        'confirmed_inputs':{},
        'assets':{},
        'revision_requests':[],
        'checks':{'functional':None,'video_decode':None,'visual_review':None,'listening_review':None,'learner_trial':None},
        'authorizations':[],
        'release':{'work_url':None,'submitted_at':None,'platform_status':None,'cover_change_status':None,'comments':[]},
        'next_action':'读取本期课程框架和上一期最终工程，完成任务卡与思维导图。',
        'scope_note':'初始化不是内容审定、生成成功、消费额度或发布授权。',
    }
    for folder in ('跟做包','视频制作','封面','发布素材'):
        (day_dir / folder).mkdir(parents=True, exist_ok=True)
    if not card_path.exists():
        card = f"""# Day{args.day} 任务卡

> 初始任务卡模板，尚未完成本期设计或用户审定。

- 系列：{SERIES}
- 课题：{title or '根据本期权威框架填写'}
- 观众：各行业想接触Vibe Coding的小白
- 上一期起点目录：{previous}
- 起点实测状态：未核验
- 当前步骤：第一步，任务卡与思维导图

## 整体目标

## 前置能力与跟做入口

## 预计正片时长与练习时长

## 开头画面与可见结果

## 各章节要点、内容、画面与跟做动作

## 量化验收与一个关键例外

## 作业与行业迁移

## 下一课承接

## 本期已授权范围与下一步

目前仅初始化，不继承上期付费或发布授权。
"""
        with card_path.open('x', encoding='utf-8') as f:
            f.write(card)
    with state_path.open('x', encoding='utf-8') as f:
        json.dump(state,f,ensure_ascii=False,indent=2)
        f.write('\n')
    print(json.dumps({'result':'initialized','directory':str(day_dir),'state':str(state_path),'card':str(card_path),'previous_exists':previous.is_dir(),'external_actions':False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
