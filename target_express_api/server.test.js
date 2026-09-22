const { formatUserResponse } = require('./server');

test('handles missing name gracefully', () => {
    // Should return a fallback like "UNKNOWN" instead of throwing a TypeError
    const result = formatUserResponse({});
    expect(result.username).toBe("UNKNOWN");
});