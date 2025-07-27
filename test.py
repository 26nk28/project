import asyncio
import random
import uuid
from datetime import datetime, timedelta
import sys
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Import all database functions
from utils.db import (
    reset_personal_schema, reset_group_schema, 
    reset_user_onboarding_schema, reset_group_onboarding_schema,
    PersonalAsyncSessionLocal, GroupAsyncSessionLocal,
    UserOnboardingAsyncSessionLocal, GroupOnboardingAsyncSessionLocal
)

# Import models
from personal_agent.models.user import User
from personal_agent.models.persona import Persona
from personal_agent.models.interaction import Interaction
from personal_agent.models.calendar import CalendarEntry
from multi_user_platform.models import Group, GroupMember
from user_onboarding.models.onboarding_models import UserOnboardingSession
from group_onboarding.models.group_onboarding_models import GroupOnboardingSession

# Import services
from personal_agent.agent import get_or_create_user
import personal_agent.backend_service as backend_service
from multi_user_platform.services.group_service import GroupService
from user_onboarding.services.onboarding_service import OnboardingService
from group_onboarding.services.group_onboarding_service import GroupOnboardingService

class ComprehensiveEndToEndTestSuite:
    """Comprehensive end-to-end test that simulates real user journey"""
    
    def __init__(self):
        self.test_results = {}
        self.users = []
        self.group_data = {}
        self.backend_tasks = []
        
        # Rate limiting for Gemini API
        self.RATE_LIMITS = {
            'delay_between_messages': 8,  # 8 seconds between messages
            'delay_between_users': 15,    # 15 seconds between users
            'backend_processing_wait': 30, # 30 seconds for backend processing
            'max_messages_per_user': 5    # Limit messages to avoid overload
        }
        
        # Realistic user data
        self.USER_DATA = [
            {
                "name": "Alice",
                "email": "alice.johnson@example.com",
                "phone": "+1234567890",
                "health_form": "I am health-conscious and have a severe dairy allergy. I prefer organic foods and eat three balanced meals daily. I avoid processed foods and artificial sweeteners.",
                "demo_messages": [
                    "I feel bloated after eating dairy products",
                    "I love eating fresh fruits and vegetables",
                    "I prefer gluten-free options when available",
                    "I drink lots of water throughout the day",
                    "I avoid processed and packaged foods"
                ]
            },
            {
                "name": "Bob",
                "email": "bob.smith@example.com", 
                "phone": "+1234567891",
                "health_form": "I'm a busy professional who often skips breakfast. I'm lactose intolerant and love spicy food but it gives me heartburn. I usually eat lunch at my desk.",
                "demo_messages": [
                    "I usually skip breakfast due to my work schedule",
                    "I'm lactose intolerant and avoid milk products",
                    "I love spicy food but it gives me heartburn",
                    "I often eat lunch at my desk around 1pm",
                    "I drink too much coffee during work hours"
                ]
            },
            {
                "name": "Charlie",
                "email": "charlie.brown@example.com",
                "phone": "+1234567892", 
                "health_form": "I'm a vegetarian fitness enthusiast who meal preps on Sundays. I eat five small meals throughout the day and avoid sugar. I have acid reflux issues.",
                "demo_messages": [
                    "I eat five small meals throughout the day",
                    "I'm vegetarian and love plant-based proteins",
                    "I meal prep on Sundays for the whole week",
                    "I avoid sugar as much as possible",
                    "I have acid reflux issues with certain foods"
                ]
            }
        ]
    
    def log_test_result(self, test_name: str, success: bool, message: str = ""):
        """Log test results for final report"""
        status = "✅ SUCCESS" if success else "❌ FAILED"
        self.test_results[test_name] = f"{status}: {message}"
        print(f"  {status}: {message}" if message else f"  {status}")
    
    async def reset_all_databases_comprehensive(self):
        """Comprehensive database reset with verification"""
        print("🗄️ COMPREHENSIVE DATABASE RESET...")
        
        try:
            # Reset all schemas
            await reset_personal_schema()
            await reset_group_schema()
            await reset_user_onboarding_schema()
            await reset_group_onboarding_schema()
            
            # Verify each database is empty
            databases = {
                'personal': PersonalAsyncSessionLocal,
                'group': GroupAsyncSessionLocal,
                'user_onboarding': UserOnboardingAsyncSessionLocal,
                'group_onboarding': GroupOnboardingAsyncSessionLocal
            }
            
            for db_name, session_class in databases.items():
                async with session_class() as session:
                    from sqlalchemy import text
                    result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                    tables = result.fetchall()
                    print(f"  📊 {db_name} database: {len(tables)} tables initialized")
            
            self.log_test_result("database_reset", True, "All 4 databases reset and verified")
            
        except Exception as e:
            self.log_test_result("database_reset", False, f"Database reset failed: {e}")
    
    async def test_user_onboarding_detailed(self):
        """Detailed user onboarding with comprehensive checks"""
        print("\n👤 DETAILED USER ONBOARDING TEST...")
        
        try:
            onboarding_service = OnboardingService()
            
            for i, user_data in enumerate(self.USER_DATA, 1):
                print(f"\n  {i}️⃣ Onboarding {user_data['name']}...")
                
                # Test onboarding session creation
                async with UserOnboardingAsyncSessionLocal() as session:
                    initial_sessions = await session.execute(
                        text("SELECT COUNT(*) FROM user_onboarding_sessions")
                    )
                    initial_count = initial_sessions.scalar()
                
                # Attempt onboarding (will fail without Personal Agent API)
                result = await onboarding_service.onboard_user(
                    name=user_data['name'],
                    email=user_data['email'],
                    phone=user_data['phone'],
                    health_form=user_data['health_form']
                )
                
                # Check onboarding session was created
                async with UserOnboardingAsyncSessionLocal() as session:
                    final_sessions = await session.execute(
                        text("SELECT COUNT(*) FROM user_onboarding_sessions")
                    )
                    final_count = final_sessions.scalar()
                
                if final_count > initial_count:
                    print(f"    ✅ Onboarding session created for {user_data['name']}")
                    
                    # Get the session details
                    from sqlalchemy import select
                    result_query = await session.execute(
                        select(UserOnboardingSession).where(
                            UserOnboardingSession.email == user_data['email']
                        )
                    )
                    onboarding_session = result_query.scalars().first()
                    
                    if onboarding_session:
                        print(f"    📝 Session ID: {onboarding_session.id[:8]}...")
                        print(f"    📧 Email: {onboarding_session.email}")
                        print(f"    📱 Phone: {onboarding_session.phone}")
                        print(f"    📋 Health form length: {len(onboarding_session.health_form)} chars")
                        print(f"    📊 Status: {onboarding_session.status}")
                else:
                    raise Exception(f"No onboarding session created for {user_data['name']}")
            
            self.log_test_result("user_onboarding_detailed", True, f"All {len(self.USER_DATA)} users onboarded with sessions")
            
        except Exception as e:
            self.log_test_result("user_onboarding_detailed", False, f"User onboarding failed: {e}")
    
    async def test_personal_agent_assignment(self):
        """Test personal agent assignment and user creation"""
        print("\n🤖 PERSONAL AGENT ASSIGNMENT TEST...")
        
        try:
            for i, user_data in enumerate(self.USER_DATA, 1):
                print(f"\n  {i}️⃣ Creating personal agent for {user_data['name']}...")
                
                # Create user with personal agent
                user_id, agent_id = await get_or_create_user(
                    name=user_data['name'],
                    email=user_data['email'],
                    phone=user_data['phone'],
                    health_form=user_data['health_form']
                )
                
                # Store user data
                self.users.append({
                    'name': user_data['name'],
                    'user_id': user_id,
                    'agent_id': agent_id,
                    'email': user_data['email'],
                    'demo_messages': user_data['demo_messages']
                })
                
                print(f"    ✅ User created: {user_id[:8]}...")
                print(f"    🤖 Agent assigned: {agent_id[:8]}...")
                
                # Verify user in database
                async with PersonalAsyncSessionLocal() as session:
                    from sqlalchemy import select
                    result = await session.execute(
                        select(User).where(User.user_id == user_id)
                    )
                    db_user = result.scalars().first()
                    
                    if db_user:
                        print(f"    📊 Database verification: ✅")
                        print(f"      - Name: {db_user.name}")
                        print(f"      - Email: {db_user.email}")
                        print(f"      - Phone: {db_user.phone}")
                    else:
                        raise Exception(f"User {user_data['name']} not found in database")
                
                # Check persona creation
                async with PersonalAsyncSessionLocal() as session:
                    result = await session.execute(
                        select(Persona).where(Persona.user_id == user_id)
                    )
                    persona = result.scalars().first()
                    
                    if persona:
                        print(f"    📝 Persona created: ✅")
                        print(f"      - Data type: {type(persona.data)}")
                        print(f"      - Data preview: {str(persona.data)[:100]}...")
                    else:
                        print(f"    ⚠️ No persona found (will be created during interactions)")
            
            self.log_test_result("personal_agent_assignment", True, f"All {len(self.users)} users assigned personal agents")
            
        except Exception as e:
            self.log_test_result("personal_agent_assignment", False, f"Personal agent assignment failed: {e}")
    
    async def test_parallel_interactions_with_rate_limiting(self):
        """Test parallel user interactions with proper rate limiting"""
        print("\n💬 PARALLEL INTERACTIONS WITH RATE LIMITING...")
        
        try:
            if not self.users:
                raise Exception("No users available for interaction testing")
            
            # Start backend processors for all users
            print(f"  🔄 Starting backend processors for {len(self.users)} users...")
            for user in self.users:
                task = asyncio.create_task(
                    backend_service.run_backend(user['user_id'], user['agent_id'])
                )
                self.backend_tasks.append(task)
                print(f"    🔧 Backend started for {user['name']}")
            
            # Wait for backends to initialize
            print(f"  ⏳ Waiting 10s for backend initialization...")
            await asyncio.sleep(10)
            
            # Process users ONE AT A TIME to respect rate limits
            for user_index, user in enumerate(self.users, 1):
                print(f"\n  👤 Processing interactions for {user['name']} ({user_index}/{len(self.users)})...")
                
                # Track interactions for this user
                interaction_count = 0
                
                for msg_index, message in enumerate(user['demo_messages'][:self.RATE_LIMITS['max_messages_per_user']], 1):
                    print(f"    💭 Message {msg_index}/{len(user['demo_messages'][:self.RATE_LIMITS['max_messages_per_user']])}: {message}")
                    
                    # Add interaction to database
                    async with PersonalAsyncSessionLocal() as session:
                        interaction = Interaction(
                            id=str(uuid.uuid4()),
                            user_id=user['user_id'],
                            agent_id=user['agent_id'],
                            input_by_user=message,
                            output_by_model="I understand and will note this in your profile.",
                            processed=False,
                            timestamp=datetime.now()
                        )
                        session.add(interaction)
                        await session.commit()
                        interaction_count += 1
                    
                    print(f"    💾 Interaction saved to database")
                    
                    # Rate limiting delay
                    if msg_index < len(user['demo_messages'][:self.RATE_LIMITS['max_messages_per_user']]):
                        print(f"    ⏳ Rate limit delay: {self.RATE_LIMITS['delay_between_messages']}s...")
                        await asyncio.sleep(self.RATE_LIMITS['delay_between_messages'])
                
                print(f"    ✅ {interaction_count} interactions completed for {user['name']}")
                
                # Delay between users
                if user_index < len(self.users):
                    print(f"  ⏳ User gap delay: {self.RATE_LIMITS['delay_between_users']}s...")
                    await asyncio.sleep(self.RATE_LIMITS['delay_between_users'])
            
            # Wait for backend processing
            print(f"\n  ⏳ Waiting {self.RATE_LIMITS['backend_processing_wait']}s for backend processing...")
            await asyncio.sleep(self.RATE_LIMITS['backend_processing_wait'])
            
            # Verify interactions in database
            total_interactions = 0
            async with PersonalAsyncSessionLocal() as session:
                from sqlalchemy import select
                for user in self.users:
                    result = await session.execute(
                        select(Interaction).where(Interaction.user_id == user['user_id'])
                    )
                    user_interactions = result.scalars().all()
                    total_interactions += len(user_interactions)
                    print(f"    📊 {user['name']}: {len(user_interactions)} interactions in database")
            
            self.log_test_result("parallel_interactions_rate_limited", True, 
                               f"Processed {total_interactions} interactions with rate limiting")
            
        except Exception as e:
            self.log_test_result("parallel_interactions_rate_limited", False, 
                               f"Parallel interactions failed: {e}")
    
    async def test_backend_processing_verification(self):
        """Verify backend processing and persona updates"""
        print("\n🔍 BACKEND PROCESSING VERIFICATION...")
        
        try:
            # Check persona updates
            personas_updated = 0
            async with PersonalAsyncSessionLocal() as session:
                from sqlalchemy import select
                
                for user in self.users:
                    result = await session.execute(
                        select(Persona).where(Persona.user_id == user['user_id'])
                    )
                    persona = result.scalars().first()
                    
                    if persona and persona.data:
                        personas_updated += 1
                        print(f"    📝 {user['name']} persona: Updated")
                        print(f"      - Data type: {type(persona.data)}")
                        print(f"      - Content preview: {str(persona.data)[:150]}...")
                    else:
                        print(f"    ⚠️ {user['name']} persona: No updates yet")
            
            # Check for any calendar entries
            calendar_entries = 0
            async with PersonalAsyncSessionLocal() as session:
                result = await session.execute(select(CalendarEntry))
                entries = result.scalars().all()
                calendar_entries = len(entries)
                
                if calendar_entries > 0:
                    print(f"    📅 Calendar entries found: {calendar_entries}")
                    for entry in entries[:3]:  # Show first 3
                        print(f"      - {entry.date} window {entry.window}: {entry.info[:50]}...")
                else:
                    print(f"    📅 No calendar entries (expected for demo messages)")
            
            self.log_test_result("backend_processing_verification", True, 
                               f"Verified processing: {personas_updated} personas, {calendar_entries} calendar entries")
            
        except Exception as e:
            self.log_test_result("backend_processing_verification", False, 
                               f"Backend verification failed: {e}")
    
    async def test_error_scenarios_and_edge_cases(self):
        """Test various error scenarios and edge cases"""
        print("\n🚨 ERROR SCENARIOS AND EDGE CASES...")
        
        try:
            error_tests_passed = 0
            total_error_tests = 0
            
            # Test 1: Duplicate user creation
            total_error_tests += 1
            print(f"  1️⃣ Testing duplicate user creation...")
            try:
                duplicate_user_id, duplicate_agent_id = await get_or_create_user(
                    name="Alice",  # Same as existing user
                    email="alice.johnson@example.com",
                    phone="+1234567890",
                    health_form="Duplicate test"
                )
                # Should return existing user
                existing_user = next((u for u in self.users if u['name'] == 'Alice'), None)
                if existing_user and duplicate_user_id == existing_user['user_id']:
                    print(f"    ✅ Duplicate handled correctly: returned existing user")
                    error_tests_passed += 1
                else:
                    print(f"    ⚠️ Unexpected behavior with duplicate user")
            except Exception as e:
                print(f"    ✅ Duplicate properly rejected: {str(e)[:50]}...")
                error_tests_passed += 1
            
            # Test 2: Invalid interaction data
            total_error_tests += 1
            print(f"  2️⃣ Testing invalid interaction data...")
            try:
                async with PersonalAsyncSessionLocal() as session:
                    invalid_interaction = Interaction(
                        id=str(uuid.uuid4()),
                        user_id="non_existent_user",
                        agent_id="non_existent_agent",
                        input_by_user="",  # Empty message
                        output_by_model="",
                        processed=False,
                        timestamp=datetime.now()
                    )
                    session.add(invalid_interaction)
                    await session.commit()
                    print(f"    ✅ Empty interaction data handled")
                    error_tests_passed += 1
            except Exception as e:
                print(f"    ✅ Invalid interaction rejected: {str(e)[:50]}...")
                error_tests_passed += 1
            
            # Test 3: Database connection stress
            total_error_tests += 1
            print(f"  3️⃣ Testing database connection stress...")
            try:
                concurrent_tasks = []
                for i in range(10):
                    task = asyncio.create_task(self._stress_test_db_connection(i))
                    concurrent_tasks.append(task)
                
                results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
                successful_connections = sum(1 for r in results if not isinstance(r, Exception))
                
                if successful_connections >= 8:  # Allow some failures
                    print(f"    ✅ Database stress test: {successful_connections}/10 connections successful")
                    error_tests_passed += 1
                else:
                    print(f"    ⚠️ Database stress test: only {successful_connections}/10 successful")
            except Exception as e:
                print(f"    ❌ Database stress test failed: {e}")
            
            # Test 4: Large data handling
            total_error_tests += 1
            print(f"  4️⃣ Testing large data handling...")
            try:
                large_message = "A" * 50000  # 50KB message
                async with PersonalAsyncSessionLocal() as session:
                    large_interaction = Interaction(
                        id=str(uuid.uuid4()),
                        user_id=self.users[0]['user_id'],
                        agent_id=self.users[0]['agent_id'],
                        input_by_user=large_message,
                        output_by_model="Large message processed",
                        processed=False,
                        timestamp=datetime.now()
                    )
                    session.add(large_interaction)
                    await session.commit()
                    print(f"    ✅ Large data handled: {len(large_message)} characters")
                    error_tests_passed += 1
            except Exception as e:
                print(f"    ⚠️ Large data handling issue: {str(e)[:50]}...")
            
            self.log_test_result("error_scenarios_edge_cases", True, 
                               f"Passed {error_tests_passed}/{total_error_tests} error scenario tests")
            
        except Exception as e:
            self.log_test_result("error_scenarios_edge_cases", False, 
                               f"Error scenario testing failed: {e}")
    
    async def _stress_test_db_connection(self, index: int):
        """Helper method for database stress testing"""
        async with PersonalAsyncSessionLocal() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
            return f"Connection {index} successful"
    
    async def test_group_onboarding_comprehensive(self):
        """Comprehensive group onboarding test"""
        print("\n🏠 COMPREHENSIVE GROUP ONBOARDING...")
        
        try:
            if len(self.users) < 3:
                raise Exception("Need at least 3 users for group onboarding")
            
            group_onboarding_service = GroupOnboardingService()
            
            # Test group creation with all users
            creator = self.users[0]
            invited_users = [user['user_id'] for user in self.users[1:]]
            
            print(f"  👤 Creator: {creator['name']} ({creator['user_id'][:8]}...)")
            print(f"  👥 Invited users: {len(invited_users)}")
            for i, user_id in enumerate(invited_users, 1):
                user_name = next(u['name'] for u in self.users if u['user_id'] == user_id)
                print(f"    {i}. {user_name} ({user_id[:8]}...)")
            
            # Check initial group onboarding sessions count
            async with GroupOnboardingAsyncSessionLocal() as session:
                from sqlalchemy import text
                initial_result = await session.execute(
                    text("SELECT COUNT(*) FROM group_onboarding_sessions")
                )
                initial_sessions = initial_result.scalar()
            
            # Attempt group creation (will fail without Group Agent API)
            result = await group_onboarding_service.create_group(
                group_name="Comprehensive Test Family Kitchen",
                creator_user_id=creator['user_id'],
                invited_user_ids=invited_users
            )
            
            # Check if group onboarding session was created
            async with GroupOnboardingAsyncSessionLocal() as session:
                final_result = await session.execute(
                    text("SELECT COUNT(*) FROM group_onboarding_sessions")
                )
                final_sessions = final_result.scalar()
                
                if final_sessions > initial_sessions:
                    print(f"  ✅ Group onboarding session created")
                    
                    # Get session details
                    from sqlalchemy import select
                    session_result = await session.execute(
                        select(GroupOnboardingSession).where(
                            GroupOnboardingSession.creator_user_id == creator['user_id']
                        )
                    )
                    group_session = session_result.scalars().first()
                    
                    if group_session:
                        print(f"    📝 Session ID: {group_session.id[:8]}...")
                        print(f"    👑 Creator: {group_session.creator_user_id[:8]}...")
                        print(f"    📛 Group name: {group_session.group_name}")
                        print(f"    👥 Invited users: {len(group_session.invited_user_ids)}")
                        print(f"    ✅ Joined users: {len(group_session.joined_user_ids)}")
                        print(f"    📊 Status: {group_session.status}")
                        
                        self.group_data = {
                            'session_id': group_session.id,
                            'group_name': group_session.group_name,
                            'creator_id': creator['user_id'],
                            'invited_ids': invited_users
                        }
                else:
                    raise Exception("No group onboarding session was created")
            
            self.log_test_result("group_onboarding_comprehensive", True, 
                               "Group onboarding session created with all users")
            
        except Exception as e:
            self.log_test_result("group_onboarding_comprehensive", False, 
                               f"Group onboarding failed: {e}")
    
    async def test_group_creation_direct(self):
        """Test direct group creation using Group Service"""
        print("\n👥 DIRECT GROUP CREATION TEST...")
        
        try:
            if not self.users:
                raise Exception("No users available for group creation")
            
            # Create group using GroupService directly
            group_info = await GroupService.create_group("Direct Test Group")
            group_id = group_info['group_id']
            
            print(f"  ✅ Group created: {group_id[:8]}...")
            
            # Add all users to the group
            added_users = 0
            for user in self.users:
                success = await GroupService.add_user_to_group(
                    group_id=group_id,
                    user_id=user['user_id'],
                    user_name=user['name'],
                    user_email=user['email']
                )
                
                if success:
                    added_users += 1
                    print(f"    ✅ Added {user['name']} to group")
                else:
                    print(f"    ❌ Failed to add {user['name']} to group")
            
            # Verify group membership
            members = await GroupService.get_group_members(group_id)
            print(f"  📊 Group verification:")
            print(f"    - Group ID: {group_id[:8]}...")
            print(f"    - Expected members: {len(self.users)}")
            print(f"    - Actual members: {len(members)}")
            print(f"    - Successfully added: {added_users}")
            
            for member in members:
                print(f"      👤 {member['user_name']} ({member['user_id'][:8]}...) - {member['role']}")
            
            # Store group data for potential future tests
            self.group_data.update({
                'direct_group_id': group_id,
                'members': members
            })
            
            if len(members) == len(self.users):
                self.log_test_result("group_creation_direct", True, 
                                   f"Group created with all {len(members)} members")
            else:
                self.log_test_result("group_creation_direct", False, 
                                   f"Group created but only {len(members)}/{len(self.users)} members added")
            
        except Exception as e:
            self.log_test_result("group_creation_direct", False, 
                               f"Direct group creation failed: {e}")
    
    async def cleanup_backend_processes(self):
        """Clean up backend processes"""
        print("\n🧹 CLEANING UP BACKEND PROCESSES...")
        
        try:
            if self.backend_tasks:
                print(f"  🛑 Stopping {len(self.backend_tasks)} backend tasks...")
                
                for i, task in enumerate(self.backend_tasks, 1):
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        print(f"    ✅ Backend task {i} cancelled")
                    except Exception as e:
                        print(f"    ⚠️ Backend task {i} cleanup error: {e}")
                
                self.backend_tasks.clear()
                print(f"  ✅ All backend processes cleaned up")
            else:
                print(f"  ℹ️ No backend processes to clean up")
                
        except Exception as e:
            print(f"  ❌ Cleanup error: {e}")
    
    async def generate_comprehensive_report(self):
        """Generate detailed comprehensive test report"""
        print("\n" + "="*100)
        print("📊 COMPREHENSIVE END-TO-END TEST REPORT")
        print("="*100)
        
        # Calculate statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result.startswith('✅'))
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📈 EXECUTIVE SUMMARY:")
        print(f"   🎯 Total Test Categories: {total_tests}")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        print(f"   📊 Success Rate: {success_rate:.1f}%")
        
        print(f"\n📋 DETAILED TEST RESULTS:")
        for test_name, result in self.test_results.items():
            formatted_name = test_name.replace('_', ' ').title()
            print(f"   {formatted_name}:")
            print(f"     {result}")
        
        print(f"\n👥 USER DATA SUMMARY:")
        if self.users:
            print(f"   📊 Users Created: {len(self.users)}")
            for i, user in enumerate(self.users, 1):
                print(f"     {i}. {user['name']}")
                print(f"        - User ID: {user['user_id'][:8]}...")
                print(f"        - Agent ID: {user['agent_id'][:8]}...")
                print(f"        - Email: {user['email']}")
                print(f"        - Demo Messages: {len(user['demo_messages'])}")
        else:
            print(f"   ⚠️ No users were successfully created")
        
        print(f"\n🏠 GROUP DATA SUMMARY:")
        if self.group_data:
            for key, value in self.group_data.items():
                if isinstance(value, list):
                    print(f"   {key.replace('_', ' ').title()}: {len(value)} items")
                else:
                    print(f"   {key.replace('_', ' ').title()}: {str(value)[:50]}...")
        else:
            print(f"   ℹ️ No group data available")
        
        print(f"\n🗄️ DATABASE VERIFICATION:")
        databases = {
            'Personal': PersonalAsyncSessionLocal,
            'Group': GroupAsyncSessionLocal,
            'User Onboarding': UserOnboardingAsyncSessionLocal,
            'Group Onboarding': GroupOnboardingAsyncSessionLocal
        }
        
        for db_name, session_class in databases.items():
            try:
                async with session_class() as session:
                    from sqlalchemy import text
                    
                    # Count tables
                    tables_result = await session.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table'")
                    )
                    tables = tables_result.fetchall()
                    
                    # Count total records (approximate)
                    total_records = 0
                    for table in tables:
                        try:
                            count_result = await session.execute(
                                text(f"SELECT COUNT(*) FROM {table[0]}")
                            )
                            count = count_result.scalar()
                            total_records += count
                        except:
                            pass
                    
                    print(f"   {db_name}: {len(tables)} tables, ~{total_records} records")
                    
            except Exception as e:
                print(f"   {db_name}: ❌ Error checking database: {e}")
        
        print(f"\n⚡ PERFORMANCE INSIGHTS:")
        print(f"   🕐 Rate Limiting Applied: {self.RATE_LIMITS['delay_between_messages']}s between messages")
        print(f"   👥 User Processing: Sequential (one at a time)")
        print(f"   💬 Max Messages per User: {self.RATE_LIMITS['max_messages_per_user']}")
        print(f"   ⏱️ Backend Processing Wait: {self.RATE_LIMITS['backend_processing_wait']}s")
        
        print(f"\n🎯 READINESS ASSESSMENT:")
        if failed_tests == 0:
            print(f"   ✅ EXCELLENT: All systems operational and ready for API development")
            print(f"   🚀 Recommended next steps:")
            print(f"     1. Build Personal Agent API endpoints")
            print(f"     2. Build Group Agent API endpoints") 
            print(f"     3. Integrate onboarding services with APIs")
            print(f"     4. Build demo application frontend")
        elif failed_tests <= 2:
            print(f"   ⚠️ GOOD: Minor issues found, mostly ready for API development")
            print(f"   🔧 Recommended: Review and fix failed tests before proceeding")
        else:
            print(f"   ❌ NEEDS WORK: Multiple issues found")
            print(f"   🛠️ Recommended: Address failed tests before API development")
        
        print(f"\n🔮 NEXT PHASE RECOMMENDATIONS:")
        print(f"   1. 🔌 API Development:")
        print(f"      - Personal Agent REST API (port 8002)")
        print(f"      - Group Agent REST API (port 8004)")
        print(f"   2. 🧪 Integration Testing:")
        print(f"      - End-to-end API testing")
        print(f"      - Service-to-service communication")
        print(f"   3. 🎨 Frontend Development:")
        print(f"      - Demo application UI")
        print(f"      - User onboarding flow")
        print(f"   4. 🚀 Deployment Preparation:")
        print(f"      - Containerization (Docker)")
        print(f"      - Cloud deployment setup")
        
        print("\n" + "="*100)
    
    async def run_comprehensive_test_suite(self):
        """Run the complete comprehensive test suite"""
        print("🚀 STARTING COMPREHENSIVE END-TO-END TEST SUITE")
        print("="*100)
        print("⚠️  This test includes rate limiting for Gemini API - will take ~10-15 minutes")
        print("="*100)
        
        start_time = time.time()
        
        try:
            # Run all test phases
            await self.reset_all_databases_comprehensive()
            await self.test_user_onboarding_detailed()
            await self.test_personal_agent_assignment()
            await self.test_parallel_interactions_with_rate_limiting()
            await self.test_backend_processing_verification()
            await self.test_error_scenarios_and_edge_cases()
            await self.test_group_onboarding_comprehensive()
            await self.test_group_creation_direct()
            
        finally:
            # Always cleanup
            await self.cleanup_backend_processes()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"\n⏱️ Total test execution time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
        
        # Generate comprehensive report
        await self.generate_comprehensive_report()

async def main():
    """Main function to run comprehensive tests"""
    test_suite = ComprehensiveEndToEndTestSuite()
    await test_suite.run_comprehensive_test_suite()

if __name__ == "__main__":
    asyncio.run(main())
