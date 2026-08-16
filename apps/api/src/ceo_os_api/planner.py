from __future__ import annotations

import json
import re
from typing import Any

from core.contracts import CapabilitySpec, ExecutionPlan, PlanStep

APP_BUNDLE_IDS = {
    "chrome": "com.google.Chrome",
    "google chrome": "com.google.Chrome",
    "safari": "com.apple.Safari",
    "textedit": "com.apple.TextEdit",
}


class DeterministicProvider:
    """Offline Phase 1 planner and test provider.

    It intentionally handles a small, explicit command set. A hosted or local LLM provider can
    implement the same ModelProvider contract without changing the runtime.
    """

    @property
    def name(self) -> str:
        return "deterministic"

    async def plan(self, message: str, capabilities: list[CapabilitySpec]) -> ExecutionPlan:
        available = {capability.name for capability in capabilities}
        lower = message.lower().strip()
        steps: list[PlanStep] = []

        competitor_match = re.search(r"research the top (ten|10) competitors", lower)
        if competitor_match and "agents.delegate.research" in available:
            items = [f"Competitor {index}" for index in range(1, 11)]
            steps.append(
                PlanStep(
                    "agents.delegate.research",
                    {"objective": message.strip(), "items": items, "worker_count": 4},
                    "Ten simulated competitor comparison records and worker evidence are returned",
                )
            )

        recall_phrases = ("what did i decide", "what do you remember", "do you remember")
        if "memory.search" in available and any(phrase in lower for phrase in recall_phrases):
            steps.append(
                PlanStep(
                    "memory.search",
                    {"query": message.strip(), "limit": 5},
                    "Relevant active memories and their provenance are returned",
                )
            )

        app_names = "|".join(
            sorted((re.escape(name) for name in APP_BUNDLE_IDS), key=len, reverse=True)
        )
        type_match = re.search(rf"^type\s+(.+?)\s+(?:in|into)\s+({app_names})$", message, re.I)
        if type_match and {"computer.app.focus", "computer.text.type"} <= available:
            bundle_id = APP_BUNDLE_IDS[type_match.group(2).lower()]
            steps.extend(
                [
                    PlanStep(
                        "computer.app.focus",
                        {"bundle_id": bundle_id},
                        f"{type_match.group(2)} is frontmost",
                    ),
                    PlanStep(
                        "computer.text.type",
                        {"bundle_id": bundle_id, "text": type_match.group(1)},
                        "The requested text is entered into the verified frontmost application",
                    ),
                ]
            )
        elif "computer.app.open" in available:
            app_match = re.search(rf"^(?:open|launch)\s+({app_names})$", message, re.I)
            if app_match:
                steps.append(
                    PlanStep(
                        "computer.app.open",
                        {"bundle_id": APP_BUNDLE_IDS[app_match.group(1).lower()]},
                        f"{app_match.group(1)} is running",
                    )
                )

        url_match = re.search(r"\b(?:browse|visit|open)\s+(https?://\S+)", message, re.I)
        if url_match and "browser.visit" in available:
            steps.append(
                PlanStep(
                    "browser.visit",
                    {"session": "ceo", "url": url_match.group(1)},
                    "The allowlisted page loads and bounded DOM content is returned",
                )
            )

        folder_match = re.search(
            r"(?:folder|directory)(?: called| named)?\s+[`'\"]?([\w.-]+)", message, re.I
        )
        if folder_match and ("create" in lower or "make" in lower):
            folder = folder_match.group(1)
            steps.append(PlanStep("files.mkdir", {"path": folder}, f"Directory {folder} exists"))
            if "readme" in lower:
                description = f"# {folder}\n\nCreated by CEO OS for: {message.strip()}\n"
                steps.append(
                    PlanStep(
                        "files.write",
                        {"path": f"{folder}/README.md", "content": description},
                        f"{folder}/README.md exists",
                    )
                )

        calc_match = re.search(r"(?:calculate|compute|what is)\s+([0-9+\-*/().% ]+)", lower)
        if calc_match:
            steps.append(
                PlanStep(
                    "calculator.evaluate",
                    {"expression": calc_match.group(1).strip()},
                    "A numeric result is returned",
                )
            )

        note_match = re.search(r"(?:note|remember)(?: that)?\s+(.+)", message, re.I)
        if note_match and not steps:
            capability = "memory.remember" if "memory.remember" in available else "notes.add"
            arguments = (
                {"content": note_match.group(1).strip()}
                if capability == "memory.remember"
                else {"text": note_match.group(1).strip()}
            )
            steps.append(PlanStep(capability, arguments, "The information is stored"))

        # Dynamic Integration & MCP capability matching
        if not steps:
            # Check for weather capability
            weather_cap = next((c for c in capabilities if "weather" in c.name), None)
            if weather_cap and ("weather" in lower or "forecast" in lower):
                city_match = re.search(
                    r"(?:weather|forecast)\s+(?:in|for|at)?\s*([a-zA-Z\s]+)", message, re.I
                )
                city = city_match.group(1).strip() if city_match else "San Francisco"
                steps.append(
                    PlanStep(
                        weather_cap.name,
                        {"city": city},
                        f"Weather forecast for {city} is returned",
                    )
                )

            # Check for platform / system info capability
            sys_info_kws = ("system info", "platform info", "host info")
            has_sys_info = "system_info.platform" in available
            if not steps and has_sys_info and any(k in lower for k in sys_info_kws):
                steps.append(
                    PlanStep(
                        "system_info.platform",
                        {},
                        "Host platform and system information are returned",
                    )
                )

            # Google Ecosystem capabilities matching
            email_kws = (
                "check email",
                "search email",
                "check inbox",
                "unread email",
                "emails about",
            )
            has_gmail = "google.gmail.search" in available
            if not steps and has_gmail and any(k in lower for k in email_kws):
                email_q_match = re.search(r"(?:for|about)\s+(.+)", message, re.I)
                eq = email_q_match.group(1).strip() if email_q_match else ""
                steps.append(
                    PlanStep(
                        "google.gmail.search",
                        {"query": eq, "max_results": 5},
                        "Matching Gmail messages are returned",
                    )
                )

            cal_kws = (
                "check calendar",
                "my schedule",
                "what's on my calendar",
                "calendar events",
                "upcoming meetings",
            )
            has_cal = "google.calendar.list" in available
            if not steps and has_cal and any(k in lower for k in cal_kws):
                steps.append(
                    PlanStep(
                        "google.calendar.list",
                        {"max_results": 10},
                        "Upcoming calendar events are returned",
                    )
                )

            # Restaurant booking workflow matching
            has_booking_wf = "workflow.restaurant.book" in available
            booking_triggers = ("book", "reserve", "reservation")
            booking_domains = ("table", "restaurant", "dinner", "osteria")
            is_booking = any(t in lower for t in booking_triggers) and any(
                d in lower for d in booking_domains
            )
            if not steps and has_booking_wf and is_booking:
                pat = (
                    r"(?:at|restaurant named|restaurant called)\s+([A-Z][a-zA-Z\s]+?)"
                    r"(?:\s+(?:tonight|tomorrow|for|at|around|,|\.|$))"
                )
                name_match = re.search(pat, message)
                if not name_match:
                    name_match = re.search(
                        r"(?:named|called)\s+([A-Za-z0-9\s]+?)(?:,|\s+call|\.|$)",
                        message,
                        re.I,
                    )
                rname = name_match.group(1).strip() if name_match else "Osteria Bella"

                size_match = re.search(r"(?:for|party of)\s+(\d+)", message, re.I)
                psize = int(size_match.group(1)) if size_match else 2

                time_match = re.search(
                    r"(?:at|around)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?)",
                    message,
                )
                ptime = time_match.group(1).strip() if time_match else "7:00 PM"

                steps.append(
                    PlanStep(
                        "workflow.restaurant.book",
                        {
                            "restaurant_name": rname,
                            "party_size": psize,
                            "time": ptime,
                            "booking_name": "Abdullah",
                        },
                        (
                            f"Autonomous restaurant booking workflow completed for {rname} "
                            f"(party of {psize} at {ptime})"
                        ),
                    )
                )

            place_kws = (
                "find restaurant",
                "search restaurant",
                "search place",
                "find place",
                "find coffee",
            )
            has_places = "google.places.search" in available
            if not steps and has_places and any(k in lower for k in place_kws):
                pat = (
                    r"(?:find|search)\s+(?:restaurant|place|coffee|cafe)?\s*"
                    r"(?:called|named|in|for)?\s*([a-zA-Z0-9\s]+)"
                )
                place_match = re.search(pat, message, re.I)
                pq = place_match.group(1).strip() if place_match else "restaurant"
                steps.append(
                    PlanStep(
                        "google.places.search",
                        {"query": pq, "location_bias": "San Francisco"},
                        f"Places matching '{pq}' are returned",
                    )
                )

            has_drive = "drive" in lower or "google doc" in lower
            if not steps and "google.drive.search" in available and has_drive:
                drive_match = re.search(r"(?:for|named|called)\s+(.+)", message, re.I)
                dq = drive_match.group(1).strip() if drive_match else ""
                steps.append(
                    PlanStep(
                        "google.drive.search",
                        {"query": dq, "max_results": 5},
                        "Matching Google Drive files are returned",
                    )
                )

            analytics_kws = ("analytics", "ga4", "website traffic", "pageviews")
            has_analytics = "google.analytics.report" in available
            if not steps and has_analytics and any(k in lower for k in analytics_kws):
                steps.append(
                    PlanStep(
                        "google.analytics.report",
                        {
                            "property_id": "properties/123456",
                            "start_date": "7daysAgo",
                            "end_date": "today",
                        },
                        "Google Analytics metrics report is returned",
                    )
                )

            has_yt = "youtube" in lower or "video search" in lower
            if not steps and "google.youtube.search" in available and has_yt:
                yt_match = re.search(r"(?:for|about)\s+(.+)", message, re.I)
                yq = yt_match.group(1).strip() if yt_match else "technology"
                steps.append(
                    PlanStep(
                        "google.youtube.search",
                        {"query": yq, "max_results": 5},
                        "Matching YouTube videos and metrics are returned",
                    )
                )

            # Telephony capabilities matching
            has_telephony = "telephony.call.outbound" in available
            call_kws = ("call ", "phone ", "dial ", "make a call", "outbound call")
            if not steps and has_telephony and any(k in lower for k in call_kws):
                phone_match = re.search(r"(\+?[0-9\-\(\)\s]{7,18})", message)
                phone_num = phone_match.group(1).strip() if phone_match else "+1-415-555-0100"
                if not phone_num.startswith("+"):
                    digits = re.sub(r"[^\d]", "", phone_num)
                    phone_num = f"+1{digits}" if len(digits) == 10 else f"+{digits}"

                obj_match = re.search(r"(?:and|to|about|asking)\s+(.+)", message, re.I)
                call_obj = obj_match.group(1).strip() if obj_match else message

                steps.append(
                    PlanStep(
                        "telephony.call.outbound",
                        {"to_number": phone_num, "objective": call_obj},
                        f"Outbound phone call to {phone_num} is completed",
                    )
                )

            # Meta Marketing capabilities matching
            has_meta_camp = "meta.campaigns.create" in available
            meta_camp_pat = (
                r"create\s+(?:a\s+)?(?:draft\s+)?(?:₹|rs\.?|inr|\$)?\s*(\d+)(?:/day)?\s*"
                r"campaign\s+targeting\s+(.+?)\s+using\s+creative\s+(.+)"
            )
            meta_match = re.search(meta_camp_pat, message, re.I)
            if not steps and has_meta_camp and meta_match:
                budget = float(meta_match.group(1))
                target_aud = meta_match.group(2).strip().rstrip(".")
                creative_name = meta_match.group(3).strip().rstrip(".")
                camp_name = f"{target_aud} Acquisition"

                steps.append(
                    PlanStep(
                        "meta.campaigns.create",
                        {
                            "account_id": "act_1019283746",
                            "name": camp_name,
                            "objective": "OUTCOME_TRAFFIC",
                            "status": "DRAFT",
                            "daily_budget": budget,
                        },
                        f"Draft campaign '{camp_name}' created with daily budget ₹{budget}",
                    )
                )
                if "meta.creatives.create" in available:
                    steps.append(
                        PlanStep(
                            "meta.creatives.create",
                            {
                                "account_id": "act_1019283746",
                                "name": creative_name,
                                "title": f"Discover {creative_name}",
                                "body": (
                                    f"Experience cutting-edge capabilities with {creative_name}."
                                ),
                                "call_to_action_type": "LEARN_MORE",
                            },
                            f"Ad creative '{creative_name}' created",
                        )
                    )
                if "meta.adsets.create" in available:
                    steps.append(
                        PlanStep(
                            "meta.adsets.create",
                            {
                                "campaign_id": "cmp_847291048",
                                "name": f"{target_aud} Targeting Ad Set",
                                "targeting": {"interests": [{"name": target_aud}]},
                                "daily_budget": budget,
                                "status": "DRAFT",
                            },
                            f"Ad set targeting '{target_aud}' created",
                        )
                    )

            has_meta_report = "meta.reporting.campaign" in available
            is_report = "meta report" in lower or "campaign report" in lower
            if not steps and has_meta_report and is_report:
                cid_match = re.search(r"(cmp_[a-zA-Z0-9]+)", message)
                cid = cid_match.group(1) if cid_match else "cmp_847291048"
                steps.append(
                    PlanStep(
                        "meta.reporting.campaign",
                        {"campaign_id": cid},
                        f"Performance report for Meta campaign {cid} is generated",
                    )
                )

            has_meta_accs = "meta.accounts.list" in available
            if not steps and has_meta_accs and ("meta accounts" in lower or "ad accounts" in lower):
                steps.append(
                    PlanStep(
                        "meta.accounts.list",
                        {},
                        "Meta advertising accounts are returned",
                    )
                )

            # Marketing Intelligence matching
            has_mkt_diag = "marketing.profit.diagnose" in available
            is_profit_query = "profit" in lower and (
                "why" in lower
                or "fall" in lower
                or "drop" in lower
                or "down" in lower
                or "diagnose" in lower
                or "change" in lower
            )
            if not steps and has_mkt_diag and is_profit_query:
                steps.append(
                    PlanStep(
                        "marketing.profit.diagnose",
                        {"date": "2026-08-15", "compare_date": "2026-08-14"},
                        "Root-cause diagnosis for profit change is returned",
                    )
                )

            has_mkt_funnel = "marketing.attribution.funnel" in available
            if not steps and has_mkt_funnel and ("attribution" in lower or "funnel" in lower):
                steps.append(
                    PlanStep(
                        "marketing.attribution.funnel",
                        {"date_start": "2026-08-01", "date_stop": "2026-08-15"},
                        "Cross-channel attribution funnel metrics are returned",
                    )
                )

            has_mkt_creatives = "marketing.creatives.analyze" in available
            is_creative_query = (
                "creative fatigue" in lower
                or "creative decay" in lower
                or "creatives analyze" in lower
            )
            if not steps and has_mkt_creatives and is_creative_query:
                steps.append(
                    PlanStep(
                        "marketing.creatives.analyze",
                        {"timeframe": "7d"},
                        "Creative fatigue and performance analysis are returned",
                    )
                )

            has_mkt_snapshot = "marketing.snapshot.get" in available
            is_snap_query = "marketing snapshot" in lower or "daily snapshot" in lower
            if not steps and has_mkt_snapshot and is_snap_query:
                steps.append(
                    PlanStep(
                        "marketing.snapshot.get",
                        {"date": "2026-08-15"},
                        "Unified daily marketing and business snapshot is returned",
                    )
                )

            # Communications Multi-Channel intent matching
            has_wa = "comms.whatsapp.send" in available
            if not steps and has_wa and "whatsapp" in lower:
                phone_match = re.search(r"(\+?[0-9\-\(\)\s]{7,18})", message)
                phone_num = phone_match.group(1).strip() if phone_match else "+1-415-555-0199"
                if not phone_num.startswith("+"):
                    digits = re.sub(r"[^\d]", "", phone_num)
                    phone_num = f"+1{digits}" if len(digits) == 10 else f"+{digits}"

                body_match = re.search(
                    r"(?:saying|with|text|message)\s+['\"]([^'\"]+)['\"]", message, re.I
                )
                wa_body = (
                    body_match.group(1).strip()
                    if body_match
                    else "Your demo is confirmed for Friday"
                )

                steps.append(
                    PlanStep(
                        "comms.whatsapp.send",
                        {"to_phone": phone_num, "body": wa_body},
                        f"WhatsApp message delivered to {phone_num}",
                    )
                )

                if "comms.followup.schedule" in available and "follow" in lower:
                    steps.append(
                        PlanStep(
                            "comms.followup.schedule",
                            {
                                "recipient_name": "Prospect",
                                "recipient_contact": phone_num,
                                "channel": "whatsapp",
                                "objective": "Demo follow-up and next steps",
                                "due_date": "2026-08-19",
                                "cadence_step": 1,
                            },
                            f"Follow-up cadence scheduled with {phone_num} in 3 days",
                        )
                    )

            has_sms = "comms.sms.send" in available
            if not steps and has_sms and "sms" in lower:
                phone_match = re.search(r"(\+?[0-9\-\(\)\s]{7,18})", message)
                phone_num = phone_match.group(1).strip() if phone_match else "+1-415-555-0100"
                body_match = re.search(
                    r"(?:saying|with|text)\s+['\"]?([^'\"]+)['\"]?", message, re.I
                )
                sms_body = body_match.group(1).strip() if body_match else message
                steps.append(
                    PlanStep(
                        "comms.sms.send",
                        {"to_phone": phone_num, "body": sms_body},
                        f"SMS text delivered to {phone_num}",
                    )
                )

            has_email = "comms.email.send" in available
            if not steps and has_email and ("send email" in lower or "email to" in lower):
                email_match = re.search(
                    r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", message
                )
                to_em = email_match.group(1) if email_match else "alex@example.com"
                subj_match = re.search(r"subject\s+['\"]([^'\"]+)['\"]", message, re.I)
                subj = subj_match.group(1) if subj_match else "Executive Update"
                b_match = re.search(r"body\s+['\"]([^'\"]+)['\"]", message, re.I)
                em_body = (
                    b_match.group(1) if b_match else "Please find the executive update attached."
                )
                steps.append(
                    PlanStep(
                        "comms.email.send",
                        {"to_email": to_em, "subject": subj, "body": em_body},
                        f"Email '{subj}' delivered to {to_em}",
                    )
                )

            has_notif = "comms.notification.broadcast" in available
            if not steps and has_notif and ("broadcast" in lower or "urgent notification" in lower):
                steps.append(
                    PlanStep(
                        "comms.notification.broadcast",
                        {
                            "title": "Executive Broadcast",
                            "message": message,
                            "severity": "critical" if "critical" in lower else "info",
                        },
                        "Multi-channel executive notification broadcast completed",
                    )
                )

            # Business Intelligence & Executive Overview intent matching
            has_exec = "business.executive.overview" in available
            is_exec_query = (
                "what's happening" in lower
                or "what is happening" in lower
                or "executive overview" in lower
                or "business status" in lower
                or "morning briefing" in lower
            )
            if not steps and has_exec and is_exec_query:
                steps.append(
                    PlanStep(
                        "business.executive.overview",
                        {"date": "2026-08-16"},
                        "Executive business overview and synthesized status returned",
                    )
                )

            has_afford = "business.finance.affordability" in available
            if not steps and has_afford and ("afford" in lower or "capital allocation" in lower):
                spend_val = 200000.0
                currency = "USD" if "$" in message or "usd" in lower else "INR"
                amt_match = re.search(
                    r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(lakh|lakhs|k|m)?", message, re.I
                )
                if amt_match:
                    raw_num = float(amt_match.group(1).replace(",", ""))
                    multiplier_str = (amt_match.group(2) or "").lower()
                    if "lakh" in multiplier_str:
                        spend_val = raw_num * 100000.0
                    elif multiplier_str == "k":
                        spend_val = raw_num * 1000.0
                    elif multiplier_str == "m":
                        spend_val = raw_num * 1000000.0
                    else:
                        spend_val = raw_num

                steps.append(
                    PlanStep(
                        "business.finance.affordability",
                        {
                            "proposed_spend": spend_val,
                            "purpose": "advertising push",
                            "currency": currency,
                        },
                        "Affordability simulation and runway forecast returned",
                    )
                )

            has_pipeline = "business.sales.pipeline" in available
            if not steps and has_pipeline and ("pipeline" in lower or "sales deals" in lower):
                steps.append(
                    PlanStep(
                        "business.sales.pipeline",
                        {},
                        "Sales pipeline summary and weighted value returned",
                    )
                )

            has_fin = "business.finance.overview" in available
            is_fin_query = (
                "financial overview" in lower or "cash runway" in lower or "cash balance" in lower
            )
            if not steps and has_fin and is_fin_query:
                steps.append(
                    PlanStep(
                        "business.finance.overview",
                        {},
                        "Financial overview and cash position returned",
                    )
                )

            has_inv = "business.operations.inventory" in available
            is_inv_query = "inventory" in lower or "low stock" in lower or "stock level" in lower
            if not steps and has_inv and is_inv_query:
                steps.append(
                    PlanStep(
                        "business.operations.inventory",
                        {"low_stock_only": True},
                        "Inventory stock levels and reorder alerts returned",
                    )
                )

            # Skills Engine intent matching
            has_skill_create = "skills.create" in available
            is_skill_create = (
                "create skill" in lower
                or "create a skill" in lower
                or "build skill" in lower
                or "new skill" in lower
            )
            if not steps and has_skill_create and is_skill_create:
                pattern = (
                    r"(?:skill|named|called)\s+['\"]?([a-zA-Z0-9_\- ]+?)['\"]?"
                    r"(?:\s+with|\s+to|\s+that|\s+for|$)"
                )
                name_match = re.search(pattern, message, re.I)
                s_name = name_match.group(1).strip() if name_match else "Custom Workflow Skill"
                steps.append(
                    PlanStep(
                        "skills.create",
                        {
                            "name": s_name,
                            "description": f"Automated procedural skill for {s_name}",
                            "steps": [
                                {
                                    "step_id": "step_1",
                                    "capability": "comms.email.send",
                                    "arguments_template": {
                                        "to_email": "{{recipient_email}}",
                                        "subject": "Welcome",
                                        "body": "Welcome to our platform",
                                    },
                                    "success_condition": "Email sent",
                                },
                                {
                                    "step_id": "step_2",
                                    "capability": "comms.followup.schedule",
                                    "arguments_template": {
                                        "channel": "email",
                                        "to_email": "{{recipient_email}}",
                                        "name": "{{name}}",
                                        "objective": "Follow up on onboarding",
                                    },
                                    "success_condition": "Follow up scheduled",
                                },
                            ],
                            "category": "workflow",
                            "tags": ["automation", "custom"],
                        },
                        f"Procedural skill '{s_name}' registered successfully",
                    )
                )

            has_skill_test = "skills.test" in available
            is_skill_test = (
                "test skill" in lower or "test the skill" in lower or "simulate skill" in lower
            )
            if not steps and has_skill_test and is_skill_test:
                id_match = re.search(
                    r"(?:skill|test)\s+['\"]?([a-zA-Z0-9_\-]+)['\"]?", message, re.I
                )
                target_id = id_match.group(1).strip() if id_match else "prepare_client_report"
                steps.append(
                    PlanStep(
                        "skills.test",
                        {
                            "skill_id": target_id,
                            "mock_inputs": {
                                "client_name": "Test Corp",
                                "recipient_email": "test@example.com",
                            },
                        },
                        f"Dry-run simulation for skill '{target_id}' completed",
                    )
                )

            has_skill_exec = "skills.execute" in available
            is_skill_exec = (
                "run skill" in lower or "execute skill" in lower or "run the skill" in lower
            )
            if not steps and has_skill_exec and is_skill_exec:
                id_match = re.search(
                    r"(?:skill|run|execute)\s+['\"]?([a-zA-Z0-9_\-]+)['\"]?", message, re.I
                )
                target_id = id_match.group(1).strip() if id_match else "prepare_client_report"
                steps.append(
                    PlanStep(
                        "skills.execute",
                        {
                            "skill_id": target_id,
                            "inputs": {
                                "client_name": "Apex Enterprise",
                                "recipient_email": "finance@apex.com",
                            },
                        },
                        f"Skill '{target_id}' executed successfully",
                    )
                )

            has_skill_ver = "skills.version" in available
            is_skill_ver = (
                "version skill" in lower or "bump skill" in lower or "upgrade skill" in lower
            )
            if not steps and has_skill_ver and is_skill_ver:
                id_match = re.search(
                    r"(?:skill|version|upgrade)\s+['\"]?([a-zA-Z0-9_\-]+)['\"]?", message, re.I
                )
                target_id = id_match.group(1).strip() if id_match else "prepare_client_report"
                steps.append(
                    PlanStep(
                        "skills.version",
                        {
                            "skill_id": target_id,
                            "new_version": "1.1.0",
                            "changelog": "Optimized execution flow and added parameter validation",
                        },
                        f"Skill '{target_id}' updated to v1.1.0",
                    )
                )

            has_skill_list = "skills.list" in available
            is_skill_list = (
                "list skills" in lower or "show skills" in lower or "skill library" in lower
            )
            if not steps and has_skill_list and is_skill_list:
                steps.append(
                    PlanStep(
                        "skills.list",
                        {},
                        "Skills library listed",
                    )
                )

            # Developer Agent API Auto-Builder intent matching
            has_api_ingest = "developer.api.ingest" in available
            is_api_ingest = (
                "ingest api" in lower
                or "add api" in lower
                or "build api" in lower
                or "auto build api" in lower
                or "generate integration" in lower
                or "openapi" in lower
            )
            if not steps and has_api_ingest and is_api_ingest:
                name_match = re.search(
                    r"(?:for|named|service|integration)\s+['\"]?([a-zA-Z0-9_\-]+)['\"]?",
                    message,
                    re.I,
                )
                svc_name = name_match.group(1).lower() if name_match else "linear"
                if svc_name in ("openapi", "swagger", "api", "specification", "the"):
                    svc_name = "linear"
                steps.append(
                    PlanStep(
                        "developer.api.ingest",
                        {
                            "service_name": svc_name,
                            "spec": {
                                "openapi": "3.0.0",
                                "info": {"title": f"{svc_name.title()} API", "version": "1.0.0"},
                                "servers": [{"url": f"https://api.{svc_name}.app/v1"}],
                                "paths": {
                                    "/issues": {
                                        "post": {
                                            "operationId": "create_issue",
                                            "summary": "Create Issue",
                                            "requestBody": {
                                                "content": {
                                                    "application/json": {
                                                        "schema": {
                                                            "type": "object",
                                                            "required": ["title"],
                                                            "properties": {
                                                                "title": {"type": "string"},
                                                                "description": {"type": "string"},
                                                            },
                                                        }
                                                    }
                                                }
                                            },
                                        },
                                        "get": {
                                            "operationId": "list_issues",
                                            "summary": "List Issues",
                                        },
                                    }
                                },
                            },
                            "auto_register": True,
                        },
                        f"API integration for '{svc_name}' synthesized, tested, and registered",
                    )
                )

            has_api_test = "developer.api.test" in available
            is_api_test = "test api" in lower or "test integration" in lower
            if not steps and has_api_test and is_api_test:
                name_match = re.search(
                    r"(?:api|service|integration)\s+['\"]?([a-zA-Z0-9_\-]+)['\"]?",
                    message,
                    re.I,
                )
                svc_name = name_match.group(1).lower() if name_match else "linear"
                steps.append(
                    PlanStep(
                        "developer.api.test",
                        {"service_name": svc_name},
                        f"Sandbox test executed for API service '{svc_name}'",
                    )
                )

            # Proactive evaluation and insights
            has_proactive_eval = "proactive.evaluate" in available
            is_proactive_eval = (
                "evaluate" in lower
                or "proactive" in lower
                or "watch business" in lower
                or "anomalies" in lower
                or "trigger" in lower
            )
            if not steps and has_proactive_eval and is_proactive_eval:
                steps.append(
                    PlanStep(
                        "proactive.evaluate",
                        {},
                        "Proactive business event triggers evaluated and insights generated",
                    )
                )
                if "proactive.insights.get" in available:
                    steps.append(
                        PlanStep(
                            "proactive.insights.get",
                            {},
                            "Active prioritized proactive insights and recommendations retrieved",
                        )
                    )

            # Proactive goal creation
            has_proactive_goal = "proactive.goal.create" in available
            is_proactive_goal = "create goal" in lower or "set goal" in lower or "add goal" in lower
            if not steps and has_proactive_goal and is_proactive_goal:
                title_match = re.search(r"(?:goal|to)\s+['\"]?([^'\",\n]+)['\"]?", message, re.I)
                goal_title = title_match.group(1).strip() if title_match else "Scale Revenue"
                steps.append(
                    PlanStep(
                        "proactive.goal.create",
                        {
                            "title": goal_title,
                            "description": f"Strategic business objective: {goal_title}",
                            "category": "sales",
                            "target_date": "2026-12-31",
                        },
                        f"Strategic goal '{goal_title}' created and tracked",
                    )
                )

            # Production hardening audit (Security, FinOps, Agent performance, Resilience)
            has_prod_audit = "production.security.audit" in available
            is_prod_audit = (
                "production" in lower
                or "hardening" in lower
                or "security audit" in lower
                or "finops" in lower
                or "cost overview" in lower
                or "agent performance" in lower
                or "resilience" in lower
            )
            if not steps and has_prod_audit and is_prod_audit:
                steps.append(
                    PlanStep(
                        "production.security.audit",
                        {"active_secret_refs": 4},
                        "Capability permissions and security posture audited",
                    )
                )
                if "production.cost.overview" in available and (
                    "cost" in lower
                    or "finops" in lower
                    or "hardening" in lower
                    or "production" in lower
                ):
                    steps.append(
                        PlanStep(
                            "production.cost.overview",
                            {},
                            "FinOps cost overview and unit economics retrieved",
                        )
                    )
                if "production.agent.performance" in available and (
                    "agent" in lower
                    or "performance" in lower
                    or "fleet" in lower
                    or "hardening" in lower
                    or "production" in lower
                ):
                    steps.append(
                        PlanStep(
                            "production.agent.performance",
                            {},
                            "Agent fleet reliability and latency profiles inspected",
                        )
                    )
                if "production.resilience.health" in available and (
                    "resilience" in lower
                    or "recovery" in lower
                    or "hardening" in lower
                    or "production" in lower
                ):
                    steps.append(
                        PlanStep(
                            "production.resilience.health",
                            {},
                            "Operational resilience, rate limits, and recovery readiness checked",
                        )
                    )

            # Agency Agents: matching, listing, inspection, and execution
            is_agency_match = "match" in lower and (
                "agency" in lower or "skill" in lower or "agent" in lower
            )
            if not steps and "agency.skills.match" in available and is_agency_match:
                steps.append(
                    PlanStep(
                        "agency.skills.match",
                        {"query": message.strip(), "top_k": 3},
                        "Optimal Agency Agent persona matched with relevance score",
                    )
                )

            is_agency_list = (
                "agency" in lower
                and ("skills" in lower or "agents" in lower or "catalog" in lower)
                and ("list" in lower or "show" in lower or "all" in lower)
            )
            if not steps and "agency.skills.list" in available and is_agency_list:
                steps.append(
                    PlanStep(
                        "agency.skills.list",
                        {},
                        "Available Agency Agent skills and specializations listed",
                    )
                )

            is_agency_exec = "agency" in lower and (
                "execute" in lower or "run" in lower or "perform" in lower
            )
            if not steps and "agency.task.execute" in available and is_agency_exec:
                steps.append(
                    PlanStep(
                        "agency.task.execute",
                        {
                            "task_id": f"task_{abs(hash(message)) % 100000}",
                            "objective": message.strip(),
                        },
                        "Task executed with matched Agency Agent persona and quality gates",
                    )
                )

            is_hermes_run = "hermes" in lower and (
                "run" in lower or "reason" in lower or "autonomous" in lower or "react" in lower
            )
            if not steps and "hermes.agent.run" in available and is_hermes_run:
                steps.append(
                    PlanStep(
                        "hermes.agent.run",
                        {
                            "task_id": f"hermes_task_{abs(hash(message)) % 100000}",
                            "objective": message.strip(),
                            "max_turns": 6,
                        },
                        "Autonomous Hermes ReAct scratchpad reasoning loop executed",
                    )
                )

            # Garry Tan gstack virtual engineering intents
            is_oh = "office-hours" in lower or "office hours" in lower
            if not steps and "gstack.office_hours" in available and is_oh:
                spec_clean = re.sub(
                    r"/(?:office-hours|office_hours)", "", message, flags=re.I
                ).strip()
                steps.append(
                    PlanStep(
                        "gstack.office_hours",
                        {"idea_or_spec": spec_clean or message.strip()},
                        "YC partner office hours discovery questions and 10-star vision formulated",
                    )
                )

            is_ceo_rev = "plan-ceo-review" in lower or "ceo review" in lower
            if not steps and "gstack.plan.ceo_review" in available and is_ceo_rev:
                spec_clean = re.sub(
                    r"/(?:plan-ceo-review|plan_ceo_review)", "", message, flags=re.I
                ).strip()
                steps.append(
                    PlanStep(
                        "gstack.plan.ceo_review",
                        {"plan_spec": spec_clean or message.strip()},
                        "CEO 10-star product strategy and scope review formulated",
                    )
                )

            is_eng_rev = "plan-eng-review" in lower or "eng review" in lower
            if not steps and "gstack.plan.eng_review" in available and is_eng_rev:
                spec_clean = re.sub(
                    r"/(?:plan-eng-review|plan_eng_review)", "", message, flags=re.I
                ).strip()
                steps.append(
                    PlanStep(
                        "gstack.plan.eng_review",
                        {"arch_spec": spec_clean or message.strip()},
                        "Engineering Manager architecture guardrail review formulated",
                    )
                )

            is_gstack_pipe = "gstack" in lower or "sdlc" in lower
            if not steps and "gstack.pipeline.run" in available and is_gstack_pipe:
                steps.append(
                    PlanStep(
                        "gstack.pipeline.run",
                        {"objective": message.strip()},
                        "Full 7-stage gstack virtual engineering pipeline executed",
                    )
                )

            # Generic tool execution: "run <tool_name>", "call <tool_name>", or direct match
            if not steps:
                for cap in capabilities:
                    if cap.name in available:
                        escaped = re.escape(cap.name)
                        cmd_pat = rf"\b(?:run|call|execute|invoke)\s+{escaped}(?:\s+(.+))?"
                        cmd_match = re.search(cmd_pat, message, re.I)
                        if cmd_match:
                            arg_text = cmd_match.group(1)
                            args: dict[str, Any] = {}
                            if arg_text:
                                try:
                                    parsed = json.loads(arg_text)
                                    args = parsed if isinstance(parsed, dict) else {"input": parsed}
                                except Exception:
                                    args = {"text": arg_text.strip()}
                            steps.append(
                                PlanStep(
                                    cap.name,
                                    args,
                                    f"Tool {cap.name} is executed successfully",
                                )
                            )
                            break

        if not steps and ("time" in lower or "date" in lower):
            steps.append(PlanStep("time.now", {}, "The current UTC time is returned"))

        return ExecutionPlan(
            objective=message.strip(),
            success_conditions=[step.success_condition for step in steps]
            or ["The request is acknowledged without an unsupported action"],
            steps=steps,
        )
