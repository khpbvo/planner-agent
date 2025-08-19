"""
Smart Planning Agent with intelligent scheduling and task management logic
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, time
from openai_agents import Agent, function_tool
from pydantic import BaseModel
import json

from ..models.task import Task, TaskPriority
from ..models.event import CalendarEvent
from ..models.context import UserPreferences, PlanningContext


class PlanningRequest(BaseModel):
    """Input for smart planning operations"""
    operation: str  # "schedule_optimal", "analyze_workload", "suggest_improvements", "find_conflicts"
    tasks: Optional[List[Dict[str, Any]]] = None
    events: Optional[List[Dict[str, Any]]] = None
    preferences: Optional[Dict[str, Any]] = None
    time_range: Optional[Dict[str, Any]] = None  # start_date, end_date
    context: Optional[Dict[str, Any]] = None


class TimeSlot(BaseModel):
    """Represents an available time slot"""
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    quality_score: float  # 0.0 to 1.0 based on user preferences
    conflicts: List[str] = []
    notes: Optional[str] = None


class PlanningRecommendation(BaseModel):
    """Planning recommendation from the smart planner"""
    type: str  # "schedule", "reschedule", "defer", "delegate", "split"
    title: str
    description: str
    impact: str  # "low", "medium", "high"
    confidence: float  # 0.0 to 1.0
    suggested_time: Optional[datetime] = None
    duration: Optional[int] = None  # minutes
    reasoning: str


@function_tool
async def smart_planning(request: PlanningRequest) -> str:
    """
    Intelligent planning operations for scheduling and task management
    
    Args:
        request: Planning request with operation details
    """
    
    try:
        if request.operation == "schedule_optimal":
            return await schedule_optimal_time(request)
        
        elif request.operation == "analyze_workload":
            return await analyze_workload(request)
        
        elif request.operation == "suggest_improvements":
            return await suggest_improvements(request)
        
        elif request.operation == "find_conflicts":
            return await find_conflicts(request)
        
        elif request.operation == "plan_day":
            return await plan_optimal_day(request)
        
        else:
            return json.dumps({
                "status": "error",
                "message": f"Unknown planning operation: {request.operation}",
                "supported_operations": [
                    "schedule_optimal", "analyze_workload", "suggest_improvements", 
                    "find_conflicts", "plan_day"
                ]
            }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Smart planning failed: {str(e)}",
            "operation": request.operation
        }, indent=2)


async def schedule_optimal_time(request: PlanningRequest) -> str:
    """Find optimal time slots for tasks based on user preferences and calendar"""
    
    # Parse user preferences
    prefs_data = request.preferences or {}
    preferences = UserPreferences(
        working_hours_start=time.fromisoformat(prefs_data.get("work_start", "09:00")),
        working_hours_end=time.fromisoformat(prefs_data.get("work_end", "17:00")),
        preferred_meeting_duration=prefs_data.get("meeting_duration", 30),
        buffer_between_events=prefs_data.get("buffer_minutes", 15)
    )
    
    # Parse time range
    time_range = request.time_range or {}
    start_date = datetime.fromisoformat(time_range.get("start_date", datetime.now().isoformat()))
    end_date = datetime.fromisoformat(time_range.get("end_date", (start_date + timedelta(days=7)).isoformat()))
    
    # Parse existing events
    existing_events = []
    for event_data in request.events or []:
        try:
            event = CalendarEvent(
                title=event_data.get("title", ""),
                start_time=datetime.fromisoformat(event_data["start_time"]),
                end_time=datetime.fromisoformat(event_data["end_time"])
            )
            existing_events.append(event)
        except:
            continue
    
    # Find available time slots
    available_slots = find_available_slots(
        start_date, end_date, existing_events, preferences
    )
    
    # Score slots based on user preferences
    scored_slots = score_time_slots(available_slots, preferences)
    
    # Match tasks to optimal slots
    recommendations = []
    for task_data in request.tasks or []:
        duration = task_data.get("estimated_duration", 60)
        priority = task_data.get("priority", "medium")
        
        best_slot = find_best_slot_for_task(scored_slots, duration, priority, preferences)
        
        if best_slot:
            recommendations.append(PlanningRecommendation(
                type="schedule",
                title=f"Schedule: {task_data.get('title', 'Task')}",
                description=f"Optimal time slot found with {best_slot.quality_score:.0%} quality score",
                impact="medium" if priority == "high" else "low",
                confidence=best_slot.quality_score,
                suggested_time=best_slot.start_time,
                duration=duration,
                reasoning=f"Selected based on working hours, calendar availability, and {priority} priority"
            ))
            
            # Remove used slot
            scored_slots = [s for s in scored_slots if s.start_time != best_slot.start_time]
    
    return json.dumps({
        "status": "success",
        "operation": "schedule_optimal",
        "recommendations": [rec.dict() for rec in recommendations],
        "available_slots_found": len(available_slots),
        "time_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        }
    }, indent=2)


async def analyze_workload(request: PlanningRequest) -> str:
    """Analyze current workload and provide insights"""
    
    tasks = request.tasks or []
    events = request.events or []
    
    # Analyze task distribution
    priority_counts = {"high": 0, "medium": 0, "low": 0}
    total_estimated_time = 0
    overdue_tasks = 0
    
    now = datetime.now()
    
    for task_data in tasks:
        priority = task_data.get("priority", "medium")
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        duration = task_data.get("estimated_duration", 60)
        total_estimated_time += duration
        
        due_date = task_data.get("due_date")
        if due_date:
            try:
                due_dt = datetime.fromisoformat(due_date)
                if due_dt < now:
                    overdue_tasks += 1
            except:
                pass
    
    # Analyze calendar load
    event_hours_per_day = {}
    for event_data in events:
        try:
            start = datetime.fromisoformat(event_data["start_time"])
            end = datetime.fromisoformat(event_data["end_time"])
            duration = (end - start).total_seconds() / 3600  # hours
            
            day = start.date()
            event_hours_per_day[day] = event_hours_per_day.get(day, 0) + duration
        except:
            continue
    
    # Calculate average daily load
    avg_daily_event_hours = sum(event_hours_per_day.values()) / max(len(event_hours_per_day), 1)
    avg_daily_task_hours = (total_estimated_time / 60) / 7  # Spread over week
    
    # Generate insights
    insights = []
    
    if overdue_tasks > 0:
        insights.append(f"⚠️ {overdue_tasks} overdue tasks need immediate attention")
    
    if priority_counts["high"] > 5:
        insights.append(f"🔥 High task load: {priority_counts['high']} high-priority tasks")
    
    if avg_daily_event_hours > 6:
        insights.append(f"📅 Heavy calendar load: {avg_daily_event_hours:.1f}h average daily meetings")
    
    if avg_daily_task_hours + avg_daily_event_hours > 8:
        insights.append("⏰ Potential overcommitment detected - consider rescheduling")
    
    if not insights:
        insights.append("✅ Workload appears manageable")
    
    return json.dumps({
        "status": "success",
        "operation": "analyze_workload",
        "analysis": {
            "task_summary": {
                "total_tasks": len(tasks),
                "priority_distribution": priority_counts,
                "estimated_total_hours": total_estimated_time / 60,
                "overdue_count": overdue_tasks
            },
            "calendar_summary": {
                "total_events": len(events),
                "avg_daily_event_hours": round(avg_daily_event_hours, 1),
                "busiest_day_hours": max(event_hours_per_day.values()) if event_hours_per_day else 0
            },
            "workload_insights": insights,
            "recommendations": generate_workload_recommendations(
                priority_counts, avg_daily_event_hours, avg_daily_task_hours, overdue_tasks
            )
        }
    }, indent=2)


def find_available_slots(
    start_date: datetime, 
    end_date: datetime, 
    events: List[CalendarEvent],
    preferences: UserPreferences,
    min_duration: int = 30
) -> List[TimeSlot]:
    """Find available time slots within date range"""
    
    slots = []
    current_date = start_date.date()
    
    while current_date <= end_date.date():
        # Skip non-working days
        if current_date.weekday() not in preferences.work_days:
            current_date += timedelta(days=1)
            continue
        
        # Find free slots in this day
        day_start = datetime.combine(current_date, preferences.working_hours_start)
        day_end = datetime.combine(current_date, preferences.working_hours_end)
        
        # Get events for this day
        day_events = [e for e in events 
                     if e.start_time.date() == current_date]
        
        # Sort events by start time
        day_events.sort(key=lambda e: e.start_time)
        
        # Find gaps between events
        current_time = day_start
        
        for event in day_events:
            if event.start_time > current_time:
                # Found a gap
                gap_duration = (event.start_time - current_time).total_seconds() / 60
                
                if gap_duration >= min_duration:
                    slots.append(TimeSlot(
                        start_time=current_time,
                        end_time=event.start_time - timedelta(minutes=preferences.buffer_between_events),
                        duration_minutes=int(gap_duration - preferences.buffer_between_events),
                        quality_score=0.8  # Will be calculated later
                    ))
            
            current_time = max(current_time, event.end_time + timedelta(minutes=preferences.buffer_between_events))
        
        # Check for slot after last event
        if current_time < day_end:
            remaining_duration = (day_end - current_time).total_seconds() / 60
            if remaining_duration >= min_duration:
                slots.append(TimeSlot(
                    start_time=current_time,
                    end_time=day_end,
                    duration_minutes=int(remaining_duration),
                    quality_score=0.8
                ))
        
        current_date += timedelta(days=1)
    
    return slots


def score_time_slots(slots: List[TimeSlot], preferences: UserPreferences) -> List[TimeSlot]:
    """Score time slots based on user preferences"""
    
    for slot in slots:
        score = 0.5  # Base score
        
        # Time of day preference
        hour = slot.start_time.hour
        
        if 9 <= hour <= 11:  # Morning prime time
            score += 0.3
        elif 14 <= hour <= 16:  # Afternoon focus time
            score += 0.2
        elif hour < 9 or hour > 17:  # Outside working hours
            score -= 0.4
        
        # Duration bonus
        if slot.duration_minutes >= 120:  # 2+ hours
            score += 0.2
        elif slot.duration_minutes >= 60:  # 1+ hour
            score += 0.1
        
        # Day of week
        if slot.start_time.weekday() in [0, 1, 2]:  # Monday-Wednesday
            score += 0.1
        elif slot.start_time.weekday() == 4:  # Friday
            score -= 0.1
        
        slot.quality_score = max(0.0, min(1.0, score))
    
    return sorted(slots, key=lambda s: s.quality_score, reverse=True)


def find_best_slot_for_task(
    slots: List[TimeSlot], 
    duration: int, 
    priority: str,
    preferences: UserPreferences
) -> Optional[TimeSlot]:
    """Find the best time slot for a specific task"""
    
    suitable_slots = [s for s in slots if s.duration_minutes >= duration]
    
    if not suitable_slots:
        return None
    
    # Priority-based selection
    if priority == "high":
        # High priority gets best available slot
        return suitable_slots[0]
    elif priority == "medium":
        # Medium priority gets good slot but not necessarily the best
        return suitable_slots[min(2, len(suitable_slots) - 1)]
    else:
        # Low priority gets any available slot
        return suitable_slots[-1]


def generate_workload_recommendations(
    priority_counts: Dict[str, int],
    avg_daily_event_hours: float,
    avg_daily_task_hours: float,
    overdue_tasks: int
) -> List[str]:
    """Generate workload management recommendations"""
    
    recommendations = []
    
    if overdue_tasks > 0:
        recommendations.append(f"Focus on completing {overdue_tasks} overdue tasks immediately")
    
    if priority_counts.get("high", 0) > 3:
        recommendations.append("Consider breaking down high-priority tasks into smaller chunks")
    
    if avg_daily_event_hours > 6:
        recommendations.append("Review meeting necessity - consider declining optional meetings")
    
    if avg_daily_task_hours + avg_daily_event_hours > 8:
        recommendations.append("Workload appears overcommitted - consider delegating or rescheduling tasks")
    
    if priority_counts.get("low", 0) > 10:
        recommendations.append("Consider batching or deferring low-priority tasks")
    
    return recommendations


async def plan_optimal_day(request: PlanningRequest) -> str:
    """Create an optimal daily schedule"""
    
    # This would integrate with the calendar and task tools
    # to create a comprehensive daily plan
    
    return json.dumps({
        "status": "success",
        "operation": "plan_day",
        "message": "Daily planning feature coming soon!",
        "suggestion": "Use schedule_optimal for now to find good time slots"
    }, indent=2)


async def suggest_improvements(request: PlanningRequest) -> str:
    """Suggest improvements to current schedule"""
    return json.dumps({
        "status": "success", 
        "operation": "suggest_improvements",
        "message": "Schedule improvement suggestions coming soon!"
    }, indent=2)


async def find_conflicts(request: PlanningRequest) -> str:
    """Find scheduling conflicts"""
    return json.dumps({
        "status": "success",
        "operation": "find_conflicts", 
        "message": "Conflict detection coming soon!"
    }, indent=2)


def create_smart_planning_tool():
    """Create the smart planning tool"""
    return smart_planning