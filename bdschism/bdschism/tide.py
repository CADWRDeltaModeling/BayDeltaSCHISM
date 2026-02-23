

class Node:
    def __init__(self, name,record_length_hours = 365*24*19):
        self.name = name
        self.record_length_hours = record_length_hours
        self.children = []
        self.parent = []

    def add_child(self, child_node):
        """Adds a child node to this node's children list."""
        self.children.append(child_node)
    def num_descendants(self):
        """Recursively counts the total number of descendants of this node."""
        count = len(self.children)
        for child in self.children:
            count += child.num_descendants()
        return count
    
    def add_parent(self, parent_node):
        """Adds a parent node to this node's parent list."""
        self.parent.append(parent_node)

    def num_ancestors(self):
        """Recursively counts the total number of ancestors of this node."""
        count = len(self.parent)
        for parent in self.parent:
            count += parent.num_ancestors()
        return count
    
    def get_ancestors(self):
        """retrieves the list of ancestors of this node."""
        ancestors = []
        for parent in self.parent:
            ancestors.append(parent)
        return ancestors
    def get_descendants(self):
        """retrieves the list of descendants of this node."""
        descendants = []
        for child in self.children:
            descendants.append(child)
        return descendants

def gen_constituents_tree():
    """
    This function generates the constituent trees of Choice of constituents and Rayleigh comparison pairs 
    It returns a list of root nodes for subtide, diurnal, semidiurnal and terdiurnal, and a list of shallow
    water constituents that have multiple parents. It is implementation from Table 1 to Table 5 in
    "MANUAL FOR TIDAL HEIGHTS ANALYSIS AND PREDICTION" by M.G.G. Foreman (1996).
    """
    nodes_tree_lst = []

    ## sub tide tree
    tree_sub = Node("Z0",record_length_hours=13)
    sa = Node("SA",record_length_hours=8766)
    ssa = Node("SSA",record_length_hours=4383)
    ssa.add_child(sa)
    tree_sub.add_child(ssa)
    msm = Node("MSM",record_length_hours=4942)
    mm = Node("MM",record_length_hours=764)
    mm.add_child(msm)
    msf = Node("MSF",record_length_hours=355)
    mf = Node("MF",record_length_hours=4383)
    msf.add_child(mf)
    msf.add_child(mm)
    tree_sub.add_child(msf)


    ## diurnal tree
    sig1 = Node("SIG1",record_length_hours=4942)
    alp1 = Node("ALP1",record_length_hours=764)
    twoq1 = Node("2Q1",record_length_hours=662)
    twoq1.add_child(sig1)
    twoq1.add_child(alp1)
    rho1 = Node("RHO1",record_length_hours=4942)
    q1 = Node("Q1",record_length_hours=662)
    q1.add_child(rho1)
    q1.add_child(twoq1)
    o1 = Node("O1",record_length_hours=328)
    tau1 = Node("TAU1",record_length_hours=4383)
    o1.add_child(q1)
    o1.add_child(tau1)
    bet1 = Node("BET1",record_length_hours=4383)
    chi1 = Node("CHI1",record_length_hours=4942)
    no1 = Node("NO1",record_length_hours=662)
    no1.add_child(chi1)
    no1.add_child(bet1)

    pi1= Node("PI1",record_length_hours= 8767)
    p1= Node("P1",record_length_hours= 4383)
    p1.add_child(pi1)

    s1= Node("S1",record_length_hours= 8767)

    psi1= Node("PSI1",record_length_hours= 8767)

    phi1= Node("PHI1",record_length_hours= 4383)

    the1= Node("THE1",record_length_hours= 4942)
    j1= Node("J1",record_length_hours= 662)
    oo1= Node("OO1",record_length_hours= 651)
    ups1= Node("UPS1",record_length_hours= 662)
    so1= Node("SO1",record_length_hours= 4383)
    oo1.add_child(ups1)
    oo1.add_child(so1)
    j1.add_child(oo1)
    j1.add_child(the1)

    k1= Node("K1",record_length_hours= 24)

    k1.add_child(o1)
    k1.add_child(p1)
    k1.add_child(j1)
    k1.add_child(no1)
    k1.add_child(phi1)
    k1.add_child(psi1)
    k1.add_child(s1)

    ## semidiurnal tree

    m2 = Node("M2",record_length_hours=13)

    oq2 = Node("OQ2",record_length_hours= 4942)
    eps2 = Node("EPS2",record_length_hours= 764)
    eps2.add_child(oq2)
    twon2 = Node("2N2",record_length_hours= 4942)
    twon2.add_child(eps2)
    mu2 = Node("MU2",record_length_hours= 764)
    mu2.add_child(twon2)
    nu2 = Node("NU2",record_length_hours= 4942)
    n2 = Node("N2",record_length_hours= 662)
    n2.add_child(nu2)
    n2.add_child(mu2)

    gam2= Node("GAM2",record_length_hours= 11326)
    h1 = Node("H1",record_length_hours= 8767)
    h1.add_child(gam2)

    h2 = Node("H2",record_length_hours= 8767)
    mks2 = Node("MKS2",record_length_hours= 4383)
    m2.add_child(n2)
    m2.add_child(h1)    
    m2.add_child(h2)
    m2.add_child(mks2)

    s2= Node("S2",record_length_hours= 355)
    lda2= Node("LDA2",record_length_hours= 4942)
    l2= Node("L2",record_length_hours= 764)
    l2.add_child(lda2)

    t2= Node("T2",record_length_hours= 8767)
    r2= Node("R2",record_length_hours= 8767)
    msn2= Node("MSN2",record_length_hours= 4383)
    eta2= Node("ETA2",record_length_hours= 662)
    eta2.add_child(msn2)
    k2= Node("K2",record_length_hours= 4383)
    k2.add_child(eta2)

    s2.add_child(k2)
    s2.add_child(l2)
    s2.add_child(t2)
    s2.add_child(r2)

    ## terdiurnal tree
    m3 = Node("M3",record_length_hours= 25)
    mo3 = Node("MO3",record_length_hours= 656)
    m3.add_child(mo3)
    so3 = Node("SO3",record_length_hours= 4383)
    mk3 = Node("MK3",record_length_hours= 656)
    mk3.add_child(so3)
    sk3 = Node("SK3",record_length_hours= 355)
    mk3.add_child(sk3)
    m3.add_child(mk3)

    nodes_tree_lst.append(tree_sub)
    nodes_tree_lst.append(k1)
    nodes_tree_lst.append(m2)
    nodes_tree_lst.append(s2)
    nodes_tree_lst.append(m3)


    ## shallow water constituents 
    shallow_group = []
    so1 = Node("SO1",record_length_hours= 4383)
    so1.add_parent(s2)
    so1.add_parent(o1)
    shallow_group.append(so1)

    mks2 = Node("MKS2",record_length_hours= 4383)
    mks2.add_parent(m2)
    mks2.add_parent(k2)
    mks2.add_parent(s2)
    shallow_group.append(mks2)

    msn2 = Node("MSN2",record_length_hours= 4383)
    msn2.add_parent(m2)
    msn2.add_parent(s2)
    msn2.add_parent(n2)
    shallow_group.append(msn2)

    mo3 = Node("MO3",record_length_hours= 656)
    mo3.add_parent(m2)
    mo3.add_parent(o1)
    shallow_group.append(mo3)

    so3 = Node("SO3",record_length_hours= 4383)
    so3.add_parent(s2)
    so3.add_parent(o1)
    shallow_group.append(so3)

    mk3 = Node("MK3",record_length_hours= 656)
    mk3.add_parent(m2)
    mk3.add_parent(k1)

    sk3 = Node("SK3",record_length_hours= 355)
    sk3.add_parent(s2)
    sk3.add_parent(k1)
    shallow_group.append(sk3)

    mn4 = Node("MN4",record_length_hours= 662)
    mn4.add_parent(m2)
    mn4.add_parent(n2)
    shallow_group.append(mn4)   

    m4 = Node("M4",record_length_hours= 25)
    m4.add_parent(m2)
    shallow_group.append(m4)

    sn4 = Node("SN4",record_length_hours= 764)
    sn4.add_parent(s2)
    sn4.add_parent(n2)
    shallow_group.append(sn4)

    ms4 = Node("MS4",record_length_hours= 355)
    ms4.add_parent(m2)
    ms4.add_parent(s2)
    shallow_group.append(ms4)

    mk4 = Node("MK4",record_length_hours= 4383)
    mk4.add_parent(m2)
    mk4.add_parent(k2)
    shallow_group.append(mk4)

    s4= Node("S4",record_length_hours= 355)
    s4.add_parent(s2)
    shallow_group.append(s4)

    sk4 = Node("SK4",record_length_hours= 4383)
    sk4.add_parent(s2)
    sk4.add_parent(k2)
    shallow_group.append(sk4)

    twomk5 = Node("2MK5",record_length_hours= 24)
    twomk5.add_parent(m2)
    twomk5.add_parent(k1)
    shallow_group.append(twomk5)

    twosk5 = Node("2SK5",record_length_hours= 178)
    twosk5.add_parent(s2)
    twosk5.add_parent(k1)
    shallow_group.append(twosk5)

    twomn6 = Node("2MN6",record_length_hours= 662)
    twomn6.add_parent(m2)
    twomn6.add_parent(n2)
    shallow_group.append(twomn6)

    m6 = Node("M6",record_length_hours= 26)
    m6.add_parent(m2)
    shallow_group.append(m6)

    twoms6 = Node("2MS6",record_length_hours= 355)
    twoms6.add_parent(m2)
    twoms6.add_parent(s2)   
    shallow_group.append(twoms6)

    twomk6 = Node("2MK6",record_length_hours= 4383)
    twomk6.add_parent(m2)
    twomk6.add_parent(k2)
    shallow_group.append(twomk6)

    twosm6= Node("2SM6",record_length_hours= 355)
    twosm6.add_parent(s2)
    twosm6.add_parent(m2)
    shallow_group.append(twosm6)

    msk6 = Node("MSK6",record_length_hours= 4383)
    msk6.add_parent(m2)
    msk6.add_parent(s2) 
    msk6.add_parent(k2)
    shallow_group.append(msk6)

    threemk7 = Node("3MK7",record_length_hours= 24)
    threemk7.add_parent(m2)
    threemk7.add_parent(k1)
    shallow_group.append(threemk7)

    m8 = Node("M8",record_length_hours= 26)
    m8.add_parent(m2)
    shallow_group.append(m8)

    return nodes_tree_lst, shallow_group



def get_constituents(record_length_hours=0):
    """
    Retrieves the names of all constituents in the astro_group and shallow_group 
    that can be analyazed by the specified record_length_hours.

    Args:    
        astro_group: list of root nodes for the main constituent groups (slow, diurnal, semidiurnal, terdiurnal).
        shallow_group: list of nodes for shallow water constituents that have multiple parents.
        record_length_hours: the length of the record in hours, used to determine which constituents can be analyzed.
    
    Returns: A sorted list of constituent names that can be analyzed with the given record length.
    """
    astro_group,shallow_group=gen_constituents_tree()
    selected_constituents = set()
    selected_constituents=get_astro_constituent_names(astro_group, record_length_hours)
 
    for node in shallow_group:
        if node.record_length_hours <= record_length_hours:
            ## get ancestors of this node and check if they satisfy the record length requirement
            ancestors = node.get_ancestors()
            all_ancestor_included = True
            for ancestor in ancestors:
                if ancestor.name not in selected_constituents:
                    all_ancestor_included = False
                    break
            if all_ancestor_included:
                selected_constituents.append(node.name)

    return sorted(selected_constituents)

def get_astro_constituent_names(astro_group, record_length_hours=0):
    """
    Recursivly Retrieves the names of all constituents in the astro_group that can be 
    analyazed by the specified record_length_hours.

    Args:
    astro_group: list of root nodes for the main constituent groups (slow, diurnal, semidiurnal, terdiurnal).
    record_length_hours: the length of the record in hours, used to determine which constituents can be analyzed.
    
    Returns: A sorted list of constituent names that can be analyzed with the given record length.
    """
    selected_constituents = set()

    for root in astro_group:
        if root.record_length_hours <= record_length_hours:
            
            selected_constituents.add(root.name)
            descendants = root.get_descendants()
            stack = descendants[:]
            while stack:
                node = stack[0]
                stack = stack[1:]
                if node.record_length_hours <= record_length_hours:
                    if (not (node.name in selected_constituents)) :
                        selected_constituents.add(node.name)
                    stack.extend(node.get_descendants())
                
                
    
    return sorted(selected_constituents)



record_length_hours = 5200
selected_constituents = get_constituents(record_length_hours)
