import memcache

client = memcache.Client([('127.0.0.1', 11211)])
client.set('foo', 'bar')
print(client.get('foo'))  # Should print 'bar'
