"""
Tests for the Chess Engine
"""

import unittest
from unittest.mock import Mock, patch

from src.engine.chess_engine import ChessEngine, GameState, ChessMove, MCTSNode
from src.ml.model_manager import ModelManager


class TestChessEngine(unittest.TestCase):
    """Test cases for the ChessEngine class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_model_manager = Mock(spec=ModelManager)
        self.engine = ChessEngine(self.mock_model_manager)
    
    def test_initialize_game(self):
        """Test game initialization."""
        state = self.engine.initialize_game()
        
        self.assertIsInstance(state, GameState)
        self.assertEqual(state.turn, "white")
        self.assertEqual(state.fullmove_number, 1)
        self.assertEqual(state.halfmove_clock, 0)
        self.assertIn("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR", state.board)
    
    def test_get_legal_moves_empty(self):
        """Test legal move generation (placeholder)."""
        state = self.engine.initialize_game()
        moves = self.engine.get_legal_moves(state)
        
        self.assertIsInstance(moves, list)
        # TODO: Update when legal move generation is implemented
    
    def test_evaluate_position(self):
        """Test position evaluation."""
        state = self.engine.initialize_game()
        self.mock_model_manager.predict_position_value.return_value = 0.5
        
        value = self.engine.evaluate_position(state)
        
        self.assertEqual(value, 0.5)
        self.mock_model_manager.predict_position_value.assert_called_once_with(state)
    
    def test_get_move_probabilities(self):
        """Test move probability prediction."""
        state = self.engine.initialize_game()
        moves = [ChessMove("e2", "e4", "P")]
        expected_probs = {moves[0]: 1.0}
        
        self.mock_model_manager.predict_move_probabilities.return_value = expected_probs
        
        probs = self.engine.get_move_probabilities(state, moves)
        
        self.assertEqual(probs, expected_probs)
        self.mock_model_manager.predict_move_probabilities.assert_called_once_with(state, moves)


class TestMCTSNode(unittest.TestCase):
    """Test cases for the MCTSNode class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.state = GameState(
            board="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            turn="white",
            castling_rights={"K": True, "Q": True, "k": True, "q": True},
            en_passant=None,
            halfmove_clock=0,
            fullmove_number=1
        )
        self.node = MCTSNode(self.state)
    
    def test_node_initialization(self):
        """Test MCTS node initialization."""
        self.assertEqual(self.node.state, self.state)
        self.assertIsNone(self.node.parent)
        self.assertIsNone(self.node.move)
        self.assertEqual(self.node.visits, 0)
        self.assertEqual(self.node.value, 0.0)
        self.assertEqual(self.node.children, [])
        self.assertEqual(self.node.untried_moves, [])
    
    def test_is_fully_expanded(self):
        """Test fully expanded check."""
        # Empty untried_moves should be fully expanded
        self.assertTrue(self.node.is_fully_expanded())
        
        # Non-empty untried_moves should not be fully expanded
        self.node.untried_moves = [ChessMove("e2", "e4", "P")]
        self.assertFalse(self.node.is_fully_expanded())


class TestModelManager(unittest.TestCase):
    """Test cases for the ModelManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        from src.ml.model_manager import ModelConfig
        self.config = ModelConfig()
        self.model_manager = ModelManager(self.config)
    
    def test_initialization(self):
        """Test model manager initialization."""
        self.assertEqual(self.model_manager.config.model_path, "models/chess_model.h5")
        self.assertEqual(self.model_manager.config.input_shape, (8, 8, 12))
    
    @patch('src.ml.model_manager.np.random.uniform')
    def test_predict_position_value_no_model(self, mock_random):
        """Test position prediction when no model is loaded."""
        mock_random.return_value = 0.42
        state = self.engine.initialize_game()
        
        value = self.model_manager.predict_position_value(state)
        
        self.assertEqual(value, 0.42)
        mock_random.assert_called_once_with(-1.0, 1.0)


if __name__ == '__main__':
    unittest.main()
