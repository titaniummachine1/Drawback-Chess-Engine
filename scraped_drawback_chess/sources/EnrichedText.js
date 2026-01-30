import React, { useState } from 'react';
import Tooltip from '@mui/material/Tooltip';

const EnrichedText = ({ children, wordTooltips }) => {
  // State to manage which tooltip is currently visible on click
  const [openTooltipIndex, setOpenTooltipIndex] = useState(null);
  // Additional state to manage hover
  const [hoverTooltipIndex, setHoverTooltipIndex] = useState(null);
  
  const processText = (text) => {
    const words = text.split(/\s+/); // Split the text into words based on spaces
    const processedWords = words.map((word, index) => {
      const cleaned_word = word.replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g,"").replace(/\s{2,}/g," ");
      const isTooltipWord = Object.keys(wordTooltips).includes(cleaned_word);
      const isPrecededByNonPawn = words[index - 1]?.toLowerCase() === "non-pawn";
      const isPrecededByOrthogonally = words[index - 1]?.toLowerCase() === "orthogonally";
      const isFollowedByMom = words[index + 1]?.toLowerCase() === "mom:";
      
      if (isTooltipWord && !isPrecededByNonPawn && !isPrecededByOrthogonally && !isFollowedByMom) {
        const tooltipText = wordTooltips[cleaned_word];
        // Determine if the tooltip should be open based on hover or click
        const isOpen = openTooltipIndex === index || hoverTooltipIndex === index;
        
        return (
          <>
            {' '}
            <Tooltip
              key={index}
              title={<span style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>{tooltipText}</span>}
              open={isOpen}
              disableFocusListener
              disableHoverListener
              disableTouchListener
              onMouseEnter={() => setHoverTooltipIndex(index)}
              onMouseLeave={() => setHoverTooltipIndex(null)}
              TransitionProps={{ timeout: 0 }}
            >
              <span
                style={{ 
                  color: 'yellow', 
                  zIndex: 9999, 
                  textDecoration: 'underline' 
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  setOpenTooltipIndex(openTooltipIndex === index ? null : index);
                }}
              >
                {word}
              </span>
            </Tooltip>
          </>
        );
      } else {
        return ` ${word}`;
      }
    });

    return <>
      {processedWords.map((word, index) => <span key={index}>{word}</span>)}
    </>;
  };

  return (
    <div onClick={() => setOpenTooltipIndex(null)}>
      {typeof children === 'string' ? processText(children) : children}
    </div>
  );
};


export default EnrichedText;