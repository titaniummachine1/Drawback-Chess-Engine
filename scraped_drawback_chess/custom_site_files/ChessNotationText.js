import React from "react";

import Typography from "@mui/material/Typography";

import "./Styles.css";


export default function ChessNotationText({text, lessMarginForPawns}) {
    return (
        <Typography variant="body1" style={{ fontSize: '24px', textAlign: 'left', marginLeft: '10px' }}>
            {text.split('').map((char, i, arr) =>
                char === '∞' ? 
                    <span key={i} style={{
                        fontSize: '30px', // Make the infinity character larger
                        position: 'relative',
                        top: '5px', // Transform infinity character downward
                    }}>{char}</span> :
                arr[i - 1] === '\\' ?
                    <span key={i} style={{
                        fontSize: '24px',
                        fontFamily: 'Cases',
                        position: 'relative',
                        top: (char === '1' || char === '0') ? '4px' : '3px',
                        transform: (char === '1' || char === '0') ? 'rotate(90deg)' : 'none',
                        ...(char === '1' || char === '0' ? { display: 'inline-block' } : {}),
                        marginRight: ((char === 'o' || char === 'p') && lessMarginForPawns) ? '-3px' : '0px',
                    }}>{char === '1' ? 'l' : char === '0' ? 'k' : char}</span> :
                    char !== '\\' ? char : ''
            )}
        </Typography>
    )
}