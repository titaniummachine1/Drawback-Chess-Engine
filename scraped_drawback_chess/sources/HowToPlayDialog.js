import React from 'react';
import EnrichedText from './EnrichedText';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogContentText,
    DialogActions,
    ThemeProvider,
    createTheme,
    Button,
} from '@mui/material';
const darkTheme = createTheme({
    palette: {
        mode: 'dark',
    },
});

const WORD_TOOLTIPS_LEMMA = {
    'piece': 'A piece is ANY chess piece, including pawns.',
    'adjacent': 'A square is adjacent to another square if they are adjacent diagonally OR orthogonally.',
    'distance': 'Distance is calculated by adding the horizontal and vertical distances ("Manhattan distance"); for example, the distance a knight moves is 3, and pieces move farther diagonally than orthogonally.',
    'value': 'Piece value is calculated using 1-3-3-5-9: pawns are 1, bishops and knights are 3, rooks are 5, and queens are 9. Kings have infinite value.',
    'rim': 'The rim is any square on the first rank, the last rank, the A-file, or the H-file.',
    'lose': 'Drawbacks that make you lose are only checked at the start of your turn.'
}

export default function HowToPlayDialog({ handleClose }) {
    return (
        <ThemeProvider theme={darkTheme}>
            <Dialog open={true} onClose={handleClose} PaperProps={{
                style: { backgroundColor: '#000033' , minWidth: '50%' },
            }}>
                <DialogTitle style={{ textAlign: 'center' }}>How To Play</DialogTitle>
                <DialogContent>
                    <DialogContentText style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: '7px' }}> Please read! There are some important differences from chess.</DialogContentText>
                    <DialogContentText style={{ marginBottom: '7px' }}>
                        <span style={{fontWeight: 'bold'}}>{`It's like chess, but you have a hidden drawback! `}</span>{`You can't see your opponent's drawback, and they can't see yours. The drawbacks are enforced by the game. You won't be able to make illegal moves, and your legal moves will be highlighted for you if you click on or pick up a piece.`}
                    </DialogContentText>
                    <DialogContentText style={{ marginBottom: '7px' }}>
                        <span style={{fontWeight: 'bold'}}>{`Checkmate and stalemate do not exist. You lose if your king is captured or if you have no legal moves (due to your drawback).`}</span>{` It is legal to ignore apparent threats to your king, move into check, move a piece that's pinned to your king, etc.`}
                    </DialogContentText>
                    <DialogContentText style={{ marginBottom: '7px' }}>
                    <span style={{fontWeight: 'bold'}}>{`Kings may be captured en passant. `}</span>{`If your king castles out of or through check, then on your opponent's next move, it can be captured by playing any move to the square it left or moved through (i.e. its home square and where the rook lands).`}
                    </DialogContentText>
                    <DialogContentText component="div" style={{ marginBottom: '7px' }}>
                    <span style={{fontWeight: 'bold'}}>{`Not all drawbacks are equal and some are harder than others. `}</span>{`If your opponent has an easier drawback than yours, you'll win more points if you win, and lose fewer if you lose. The stronger player will tend to get a more significant drawback.`}
                    </DialogContentText>
                    <DialogContentText>
                    <EnrichedText wordTooltips={WORD_TOOLTIPS_LEMMA}>
                        {`Mouse over highlighted terms -- such as lose, piece, adjacent, distance, value, and rim -- to display more information about them.`}
                    </EnrichedText>
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button variant="contained" onClick={handleClose}>Close</Button>
                </DialogActions>
            </Dialog>
        </ThemeProvider>
    )
}