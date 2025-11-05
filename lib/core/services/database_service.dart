import 'dart:convert';
import 'dart:math';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:path/path.dart' as p;
import 'package:sqflite_sqlcipher/sqflite.dart';

class DatabaseService {
  DatabaseService._();

  static final DatabaseService instance = DatabaseService._();

  static const String _dbName = 'mental_health.db';
  static const int _dbVersion = 2;
  static const String _encryptionKeyStorageKey = 'db_encryption_key';

  Database? _database;
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();

  Future<Database> get database async {
    if (_database != null) {
      return _database!;
    }
    _database = await _openDatabase();
    return _database!;
  }

  Future<void> close() async {
    if (_database != null) {
      await _database!.close();
      _database = null;
    }
  }

  Future<Database> _openDatabase() async {
    final databasesPath = await getDatabasesPath();
    final path = p.join(databasesPath, _dbName);
    final encryptionKey = await _getOrCreateEncryptionKey();

    return openDatabase(
      path,
      password: encryptionKey,
      version: _dbVersion,
      onCreate: _onCreate,
      onUpgrade: _onUpgrade,
    );
  }

  Future<void> _onCreate(Database db, int version) async {
    // Mood entries table
    await db.execute('''
      CREATE TABLE mood_entries (
        id TEXT PRIMARY KEY,
        emotion TEXT NOT NULL,
        stress_level INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        note TEXT
      )
    ''');

    // Chat messages table
    await db.execute('''
      CREATE TABLE chat_messages (
        id TEXT PRIMARY KEY,
        data TEXT NOT NULL
      )
    ''');
  }

  Future<void> _onUpgrade(Database db, int oldVersion, int newVersion) async {
    // Migration from v1 to v2: Add chat_messages table
    if (oldVersion < 2) {
      await db.execute('''
        CREATE TABLE chat_messages (
          id TEXT PRIMARY KEY,
          data TEXT NOT NULL
        )
      ''');
    }
  }

  Future<String> _getOrCreateEncryptionKey() async {
    var key = await _secureStorage.read(key: _encryptionKeyStorageKey);
    if (key != null && key.isNotEmpty) {
      return key;
    }

    final random = Random.secure();
    final bytes = List<int>.generate(32, (_) => random.nextInt(256));
    key = base64UrlEncode(bytes);
    await _secureStorage.write(key: _encryptionKeyStorageKey, value: key);
    return key;
  }
}
