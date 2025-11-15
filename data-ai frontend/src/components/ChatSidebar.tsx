import { useState, useMemo } from 'react';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import { Input } from './ui/input';
import { 
  MessageSquarePlus, 
  LogOut, 
  MessageSquare, 
  Database, 
  Trash2,
  Pin,
  Archive,
  Search,
  Filter,
  SortAsc,
  FileText
} from 'lucide-react';
import { ChatSession, DatabaseConnection } from './ChatInterface';
import { DatabaseManagement } from './DatabaseManagement';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from './ui/dropdown-menu';
import { Badge } from './ui/badge';

interface ChatSidebarProps {
  chatSessions: ChatSession[];
  currentChatId: string;
  onNewChat: () => void;
  onSelectChat: (chatId: string) => void;
  onDeleteChat: (chatId: string) => void;
  onLogout: () => void;
  dbConnections: DatabaseConnection[];
  onAddDbConnection: (connection: Omit<DatabaseConnection, 'id'>) => void;
  onUpdateDbConnection: (id: string, updates: Partial<DatabaseConnection>) => void;
  onDeleteDbConnection: (id: string) => void;
  onSetDefaultDb: (id: string) => void;
  onTogglePin?: (chatId: string) => void;
  onToggleArchive?: (chatId: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: (collapsed: boolean) => void;
}

type SortOption = 'recent' | 'oldest' | 'name';
type FilterOption = 'all' | 'pinned' | 'archived' | 'active';

export function ChatSidebar({
  chatSessions,
  currentChatId,
  onNewChat,
  onSelectChat,
  onDeleteChat,
  onLogout,
  dbConnections,
  onAddDbConnection,
  onUpdateDbConnection,
  onDeleteDbConnection,
  onSetDefaultDb,
  onTogglePin,
  onToggleArchive,
  isCollapsed,
  onToggleCollapse,
}: ChatSidebarProps) {
  const [activeTab, setActiveTab] = useState('chats');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<SortOption>('recent');
  const [filterBy, setFilterBy] = useState<FilterOption>('active');

  // Filter, search, and sort chat sessions
  const processedChatSessions = useMemo(() => {
    let filtered = chatSessions;

    // Apply filter
    switch (filterBy) {
      case 'pinned':
        filtered = filtered.filter(chat => chat.isPinned);
        break;
      case 'archived':
        filtered = filtered.filter(chat => chat.isArchived);
        break;
      case 'active':
        filtered = filtered.filter(chat => !chat.isArchived);
        break;
      default: // 'all'
        break;
    }

    // Apply search
    if (searchQuery.trim()) {
      filtered = filtered.filter(chat =>
        chat.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        chat.preview.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Apply sort
    const sorted = [...filtered].sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'oldest':
          return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
        case 'recent':
        default:
          return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
      }
    });

    // Ensure pinned chats are always at the top when not filtered by archived
    if (filterBy !== 'archived') {
      return sorted.sort((a, b) => {
        if (a.isPinned && !b.isPinned) return -1;
        if (!a.isPinned && b.isPinned) return 1;
        return 0;
      });
    }

    return sorted;
  }, [chatSessions, searchQuery, sortBy, filterBy]);

  const getArtifactCount = (chat: ChatSession): number => {
    return chat.messages.filter(msg => msg.artifact).length;
  };

  const getAssociatedDb = (chat: ChatSession): string | null => {
    if (chat.activeDbId) {
      const db = dbConnections.find(conn => conn.id === chat.activeDbId);
      return db ? db.name : null;
    }
    return null;
  };

  return (
    <div 
      className="w-80 bg-gradient-to-b from-slate-50 to-slate-100 border-r border-slate-200 flex flex-col shadow-lg"
    >
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-slate-200 bg-white/50 backdrop-blur">
          <h2 className="text-black mb-4 text-center">Chat Assistant</h2>
          
          <TabsList className="grid w-full grid-cols-2 mb-4">
            <TabsTrigger value="chats" className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              Chats
            </TabsTrigger>
            <TabsTrigger value="databases" className="flex items-center gap-2">
              <Database className="h-4 w-4" />
              Databases
            </TabsTrigger>
          </TabsList>

          {activeTab === 'chats' && (
            <>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      onClick={onNewChat}
                      className="w-full bg-black hover:bg-gray-800 text-white rounded-xl shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center gap-2 mb-3"
                    >
                      <MessageSquarePlus className="h-4 w-4" />
                      New Chat
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Start a new conversation</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              {/* Search Bar */}
              <div className="relative mb-3">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  type="text"
                  placeholder="Search chats..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 rounded-xl bg-white border-slate-300"
                />
              </div>

              {/* Filter and Sort Controls */}
              <div className="flex gap-2">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="flex-1 rounded-lg border-slate-300">
                      <Filter className="h-3 w-3 mr-1" />
                      {filterBy === 'all' ? 'All' : filterBy === 'pinned' ? 'Pinned' : filterBy === 'archived' ? 'Archived' : 'Active'}
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    <DropdownMenuLabel>Filter by</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => setFilterBy('active')}>
                      Active Chats
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setFilterBy('pinned')}>
                      Pinned Only
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setFilterBy('archived')}>
                      Archived Only
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setFilterBy('all')}>
                      All Chats
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="flex-1 rounded-lg border-slate-300">
                      <SortAsc className="h-3 w-3 mr-1" />
                      {sortBy === 'recent' ? 'Recent' : sortBy === 'oldest' ? 'Oldest' : 'Name'}
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuLabel>Sort by</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => setSortBy('recent')}>
                      Most Recent
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setSortBy('oldest')}>
                      Oldest First
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setSortBy('name')}>
                      Name (A-Z)
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </>
          )}
        </div>

        {/* Tab Content */}
        <TabsContent value="chats" className="flex-1 overflow-hidden m-0">
          <ScrollArea className="h-full px-3 py-4">
            {processedChatSessions.length === 0 ? (
              <div className="text-center py-8 px-4">
                <MessageSquare className="h-12 w-12 mx-auto text-slate-300 mb-3" />
                <p className="text-slate-500 mb-1">No chats found</p>
                <p className="text-xs text-slate-400">
                  {searchQuery ? 'Try a different search term' : 'Start a new conversation'}
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {processedChatSessions.map(chat => {
                  const artifactCount = getArtifactCount(chat);
                  const associatedDb = getAssociatedDb(chat);

                  return (
                    <div
                      key={chat.id}
                      className={`w-full text-left p-2 rounded-xl transition-all duration-200 group hover:shadow-md border ${
                        currentChatId === chat.id
                          ? 'bg-white shadow-md border-2 border-slate-300'
                          : 'bg-white/60 hover:bg-white border-slate-200'
                      } ${chat.isArchived ? 'opacity-60' : ''}`}
                    >
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => onSelectChat(chat.id)}
                          className="flex items-center gap-2 flex-1 min-w-0"
                        >
                          <div className={`p-1.5 rounded-lg flex-shrink-0 ${
                            currentChatId === chat.id
                              ? 'bg-black text-white'
                              : 'bg-slate-100 text-slate-600 group-hover:bg-slate-200'
                          }`}>
                            <MessageSquare className="h-3.5 w-3.5" />
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1">
                              {chat.isPinned && <Pin className="h-3 w-3 text-blue-600 fill-blue-600 flex-shrink-0" />}
                              {chat.isArchived && <Archive className="h-3 w-3 text-amber-600 flex-shrink-0" />}
                              <span className="text-black truncate text-sm">{chat.name}</span>
                            </div>
                            
                            {/* Date only */}
                            <div className="text-xs text-slate-400">
                              {new Date(chat.timestamp).toLocaleDateString()}
                            </div>
                          </div>
                        </button>
                        
                        {/* Action buttons */}
                        <div className="flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          {onTogglePin && (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      onTogglePin(chat.id);
                                    }}
                                    variant="ghost"
                                    size="sm"
                                    className={`h-7 w-7 p-0 ${
                                      chat.isPinned 
                                        ? 'text-blue-600 hover:bg-blue-50' 
                                        : 'text-slate-400 hover:bg-slate-100'
                                    }`}
                                  >
                                    <Pin className={`h-3 w-3 ${chat.isPinned ? 'fill-blue-600' : ''}`} />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>{chat.isPinned ? 'Unpin' : 'Pin'} chat</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          )}

                          {onToggleArchive && (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      onToggleArchive(chat.id);
                                    }}
                                    variant="ghost"
                                    size="sm"
                                    className={`h-7 w-7 p-0 ${
                                      chat.isArchived 
                                        ? 'text-amber-600 hover:bg-amber-50' 
                                        : 'text-slate-400 hover:bg-slate-100'
                                    }`}
                                  >
                                    <Archive className="h-3 w-3" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>{chat.isArchived ? 'Unarchive' : 'Archive'} chat</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          )}

                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    onDeleteChat(chat.id);
                                  }}
                                  disabled={chatSessions.length === 1}
                                  variant="ghost"
                                  size="sm"
                                  className={`h-7 w-7 p-0 ${
                                    chatSessions.length === 1 
                                      ? 'hidden' 
                                      : 'text-slate-400 hover:text-red-600 hover:bg-red-50'
                                  }`}
                                >
                                  <Trash2 className="h-3 w-3" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>{chatSessions.length === 1 ? 'Cannot delete last chat' : 'Delete chat'}</p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </ScrollArea>
        </TabsContent>

        <TabsContent value="databases" className="flex-1 overflow-hidden m-0">
          <DatabaseManagement
            dbConnections={dbConnections}
            onAddConnection={onAddDbConnection}
            onUpdateConnection={onUpdateDbConnection}
            onDeleteConnection={onDeleteDbConnection}
            onSetDefaultDb={onSetDefaultDb}
          />
        </TabsContent>
      </Tabs>

      {/* Footer */}
      <div className="p-4 border-t border-slate-200 bg-white/50 backdrop-blur">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                onClick={onLogout}
                variant="outline"
                className="w-full border-slate-300 hover:bg-slate-100 rounded-xl flex items-center justify-center gap-2"
              >
                <LogOut className="h-4 w-4" />
                Logout
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Sign out of your account</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>
  );
}