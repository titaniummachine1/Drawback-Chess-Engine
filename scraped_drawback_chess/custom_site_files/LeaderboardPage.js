import { useState, useEffect } from 'react';
import { fetchWrapper, getUsername } from './Helpers';
import { Box, Grid, Paper, Typography } from '@mui/material';

const LeaderboardGrid = ({ leaderboard }) => {
    return (
        <Box sx={{ maxWidth: 'lg', margin: 'auto', marginBottom: '20px' }}>
            <Typography align="center" variant="h4" gutterBottom>
                Leaderboard
            </Typography>
            <Grid container spacing={2}>
                <Grid item xs={12}>
                    <Paper elevation={2} sx={{ borderRadius: 2, border: 1, borderColor: 'divider' }}>
                        <Grid container>
                            <Grid item xs={4}><Typography align="center" variant="h6">Rank</Typography></Grid>
                            <Grid item xs={4}><Typography align="center" variant="h6">Name</Typography></Grid>
                            <Grid item xs={4}><Typography align="center" variant="h6">Elo</Typography></Grid>
                        </Grid>
                    </Paper>
                </Grid>
                {leaderboard.map((row, index) => (
                    <Grid item xs={12} key={index}>
                        <Paper elevation={2} sx={{ borderRadius: 2, border: 1, borderColor: 'divider', mt: 1 }}>
                            <Grid container alignItems="center">
                                <Grid item xs={4}><Typography align="center">{index + 1}</Typography></Grid>
                                <Grid item xs={4}><Typography align="center">{(index === 0 ? '👑' : '') + row.displayName + (index === 0 ? '👑' : '')} </Typography></Grid>
                                <Grid item xs={4}><Typography align="center">{row.elo}</Typography></Grid>
                            </Grid>
                        </Paper>
                    </Grid>
                ))}
            </Grid>
        </Box>
    );
};

export default function LeaderboardPage() {
    const [leaderboard, setLeaderboard] = useState(null);
    const [percentile, setPercentile] = useState(null);
    const [loading, setLoading] = useState(true);

    let username = getUsername(20);

    useEffect(() => {
        fetchWrapper('/leaderboard', { username }, 'GET')
            .then(response => {
                if (response.success) {
                    setLeaderboard(response.leaderboard);
                    setPercentile(response.percentile);
                    setLoading(false);
                } else {
                    console.error(response.error);
                }
            });
    }, []);

    if (loading) {
        return <div>Loading...</div>;
    }

    return (
        <div>
            <Typography align="center" variant="h6" gutterBottom>
                {percentile ? `You are roughly in the top ${percentile}% of players` : "Play more games to see your rank!"}
            </Typography>
            <LeaderboardGrid leaderboard={leaderboard} />
        </div>
    );
}
