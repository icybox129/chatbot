data "aws_availability_zones" "available" {
  state = "available"
}

##############
# NETWORKING #
##############

resource "aws_vpc" "vpc" {
  cidr_block           = var.vpc_cidr_block
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.naming_prefix}-vpc"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.vpc.id

  tags = {
    Name = "${var.naming_prefix}-igw"
  }
}

#################
# PUBLIC SUBNET #
#################

# One public usbnet per AZ

resource "aws_subnet" "public" {
  count                   = var.az_count
  cidr_block              = cidrsubnet(var.vpc_cidr_block, 8, var.az_count + count.index)
  vpc_id                  = aws_vpc.vpc.id
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.naming_prefix}-public-subnet"
  }
}

#######################
# PUBLIC ROUTE TABLES #
#######################

# Route table with entry to the Internet Gateway

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "${var.naming_prefix}-public-rt"
  }
}

# Associate the public route table with the public subnets

resource "aws_route_table_association" "public" {
  count          = var.az_count
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

##############
# ELASTIC IP #
##############

# Creates one Elastic IP per AZ (one for each NAT Gateway)

resource "aws_eip" "nat_eip" {
  count = var.az_count
  vpc   = true

  tags = {
    Name = "${var.naming_prefix}-nat-eip"
  }
}

###############
# NAT GATEWAY #
###############

# Creates one NAT Gateway per AZ

resource "aws_nat_gateway" "nat" {
  count         = var.az_count
  allocation_id = aws_eip.nat_eip[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name = "${var.naming_prefix}-nat"
  }
}

###################
# PRIVATE SUBNETS #
###################

resource "aws_subnet" "private" {
  count             = var.az_count
  cidr_block        = cidrsubnet(var.vpc_cidr_block, 8, var.az_count + count.index + var.az_count)
  vpc_id            = aws_vpc.vpc.id
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.naming_prefix}-private-subnet"
  }
}

########################
# PRIVATE ROUTE TABLES #
########################

# Route table with entry to the NAT Gateway

resource "aws_route_table" "private" {
  count  = var.az_count
  vpc_id = aws_vpc.vpc.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat[count.index].id
  }

  tags = {
    Name = "${var.naming_prefix}-private-rt"
  }
}

# Associate the private route table with the private subnets

resource "aws_route_table_association" "private" {
  count          = var.az_count
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}
