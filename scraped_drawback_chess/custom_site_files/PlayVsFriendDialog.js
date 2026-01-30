import React, { useState, useEffect } from 'react';
import { 
    Dialog, 
    DialogTitle, 
    DialogContent, 
    DialogContentText, 
    createTheme, 
    ThemeProvider, 
    Typography,
    DialogActions,
    Button,
    Grid,
    Avatar,
    Card,
    CardContent,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { fetchWrapper } from './Helpers';
import CrossedSwords from './assets/crossed_swords.png'; // import the image
import { FriendLinkDialog } from './AddFriendDialog';
import { HostGameDialog } from './HostGameDialog';


const darkTheme = createTheme({
  palette: {
    mode: 'dark',
  },
});

function FriendsList({ username, handleClose, showMessage, showError, setChallengeFriendshipId }) {
  const [friends, setFriends] = useState([]);

  useEffect(() => {
    fetchWrapper('/friendships', { username }, 'GET').then((data) => {
      setFriends(data?.friendships || []);
    });
  }, [username]);

  const handleChallenge = (friendship) => {
    fetchWrapper(`/challenge/${friendship.id}`, { username, friendship }, 'POST', 5050)
    .then((response) => {
      if (response.error) {
        showError(response.error);
      }
      else {
        handleClose();
        showMessage('Challenge sent!');
        setChallengeFriendshipId(friendship.id);
      }
    })
  }

  return (
    friends.length > 0 ? <Grid container spacing={2}>
      {friends.map((friend) => (
        <Grid item key={friend.id}>
          <Card>
            <CardContent>
              <Grid container alignItems="center" spacing={2}>
                <Grid item>
                  <Typography variant="h6">{friend.displayName}</Typography>
                </Grid>
                {!friend.pending && (
                  <Grid item>
                    <Button variant="contained" onClick={() => handleChallenge(friend)}>
                      <Avatar src={CrossedSwords} alt="Challenge" />
                    </Button>
                  </Grid>
                )}
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid> : (
      <Typography variant="body1">
        Add some friends to challenge them!
      </Typography>
    )
  );
}

export function PlayVsFriendDialog({ open, handleClose, username, showMessage, setChallengeFriendshipId, showError }) {
    const [friendLinkDialogOpen, setFriendLinkDialogOpen] = useState(false);
    const [hostGameDialogOpen, setHostGameDialogOpen] = useState(false);

    return (
      <>
        <ThemeProvider theme={darkTheme}>
            <Dialog open={open} onClose={handleClose} PaperProps={{ 
                style: { backgroundColor: '#000033' }, 
            }}>
                <DialogTitle style={{ textAlign: 'center' }}>Challenge a friend</DialogTitle>
                <DialogContent>
                    <DialogContentText style={{ marginBottom: '7px' , textAlign: 'center' }}>
                        Time controls of a friendly challenge are based on your most recently hosted game.
                    </DialogContentText>   
                    <FriendsList username={username} handleClose={handleClose} showMessage={showMessage} showError={showError} setChallengeFriendshipId={setChallengeFriendshipId} />
                    <Typography variant="body1" style={{ marginTop: '1em' }}>
                      Add a new friend:
                    </Typography>
                    <br />
                    <Button variant="contained" onClick={() => setFriendLinkDialogOpen(true)}>
                      Add friend
                    </Button>
                    <br />
                    <Typography variant="body1" style={{ marginTop: '1em' }}>
                      Or host a game and send a link to the game to your friend:
                    </Typography>
                    <br />
                    <Button variant="contained" onClick={() => setHostGameDialogOpen(true)}>
                      Host game
                    </Button>
                </DialogContent>
            </Dialog>
        </ThemeProvider>
        {friendLinkDialogOpen && <FriendLinkDialog open={friendLinkDialogOpen} handleClose={() => setFriendLinkDialogOpen(false)} username={username} />}
        {hostGameDialogOpen && <HostGameDialog 
          open={hostGameDialogOpen} 
          handleClose={() => setHostGameDialogOpen(false)} 
          username={username} 
          showError={showError}
          vsAi={false}
        />}
      </>
    );
}
