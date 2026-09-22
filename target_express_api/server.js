function formatUserResponse(user) {
    // Check if user and name properties are defined before calling toUpperCase
    return {
        username: user && user.name ? user.name.toUpperCase() : 'UNKNOWN',
        status: "active"
    };
}
module.exports = { formatUserResponse };
