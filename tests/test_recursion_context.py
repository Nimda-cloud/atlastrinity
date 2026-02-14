
import unittest
from src.brain.core.orchestration.context import SharedContext

class TestRecursionContext(unittest.TestCase):
    def test_push_pop_goal_integrity(self):
        """Verify that push/pop correctly maintains goal stack and step state."""
        ctx = SharedContext()
        ctx.max_recursive_depth = 5
        
        # 1. Root Level (Depth 0)
        ctx.push_goal("Root Goal", total_steps=10)
        ctx.current_step_id = 5
        self.assertEqual(ctx.current_goal, "Root Goal")
        self.assertEqual(ctx.recursive_depth, 0)
        self.assertEqual(ctx.total_steps, 10)
        
        # 2. Enter Recursion (First Level sub-goal -> Depth 1)
        ctx.push_goal("Sub Goal 1", total_steps=3)
        # Check parent state preservation
        self.assertEqual(len(ctx._step_state_stack), 1)
        self.assertEqual(ctx._step_state_stack[0], (10, 5))
        
        # Check new state
        self.assertEqual(ctx.current_goal, "Sub Goal 1")
        self.assertEqual(ctx.parent_goal, "Root Goal")
        self.assertEqual(ctx.recursive_depth, 1)
        self.assertEqual(ctx.total_steps, 3)
        self.assertEqual(ctx.current_step_id, 0)
        
        # Advance step in sub-goal
        ctx.advance_step()
        ctx.advance_step()
        self.assertEqual(ctx.current_step_id, 2)
        
        # 3. Enter Deep Recursion (Second Level sub-goal -> Depth 2)
        ctx.push_goal("Sub Goal 1.1", total_steps=2)
        self.assertEqual(len(ctx._step_state_stack), 2)
        self.assertEqual(ctx._step_state_stack[1], (3, 2))
        self.assertEqual(ctx.recursive_depth, 2)
        
        # 4. Pop Sub-Goal 1.1 -> Return to Sub Goal 1 (Depth 1)
        popped = ctx.pop_goal()
        self.assertEqual(popped, "Sub Goal 1.1")
        self.assertEqual(ctx.current_goal, "Sub Goal 1")
        self.assertEqual(ctx.recursive_depth, 1)
        # Verify state restoration
        self.assertEqual(ctx.total_steps, 3)
        self.assertEqual(ctx.current_step_id, 2)
        self.assertEqual(len(ctx._step_state_stack), 1)
        
        # 5. Pop Sub-Goal 1 -> Return to Root (Depth 0)
        popped = ctx.pop_goal()
        self.assertEqual(popped, "Sub Goal 1")
        self.assertEqual(ctx.current_goal, "Root Goal")
        self.assertEqual(ctx.recursive_depth, 0)
        # Verify state restoration
        self.assertEqual(ctx.total_steps, 10)
        self.assertEqual(ctx.current_step_id, 5)
        self.assertEqual(len(ctx._step_state_stack), 0)

    def test_max_recursion_depth(self):
        """Verify RecursionError is raised when exceeding max depth."""
        ctx = SharedContext()
        ctx.max_recursive_depth = 3
        
        ctx.push_goal("L0") # Depth 0
        ctx.push_goal("L1") # Depth 1
        ctx.push_goal("L2") # Depth 2
        
        self.assertEqual(ctx.recursive_depth, 2)
        
        # Should fail when pushing L3 (depth 3)
        with self.assertRaises(RecursionError) as cm:
            ctx.push_goal("L3")
        
        self.assertIn("exceeds max 3", str(cm.exception))
        self.assertEqual(ctx.recursive_depth, 2)  # Should not have changed

    def test_goal_vector_generation(self):
        """Verify goal vector generation logic."""
        ctx = SharedContext()
        
        # Root level - No vector
        ctx.push_goal("Make a sandwich")
        self.assertEqual(ctx.get_goal_vector(), "")
        
        # Level 2 - Vector acts as compass
        ctx.push_goal("Slice bread")
        vector = ctx.get_goal_vector()
        
        self.assertIn("🧭 GOAL VECTOR", vector)
        self.assertIn("Parent Goal: Make a sandwich", vector)
        self.assertIn("Current Sub-Goal: Slice bread", vector)
        self.assertIn("prioritize the approach that aligns with the Parent Goal", vector)
        
        # Check context injection
        context_str = ctx.get_goal_context()
        self.assertIn("🧭 GOAL VECTOR", context_str)
        
        # Level 3 - Full chain
        ctx.push_goal("Find knife")
        vector_l3 = ctx.get_goal_vector()
        
        self.assertIn("Full goal chain", vector_l3)
        self.assertIn("● Make a sandwich", vector_l3)
        self.assertIn("└─ Slice bread", vector_l3)
        self.assertIn("└─ Find knife", vector_l3)

if __name__ == '__main__':
    unittest.main()
